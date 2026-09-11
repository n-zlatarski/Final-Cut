"""Pack generated video-reference choreography; mechanical operations only.
Original art is retained. One scale per direction, exact native sole anchors.
"""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from build_jinwoo_assets import CELL, PIVOT, BODY_HEIGHT, DIRECTIONS, COLORS
from build_jinwoo_dagger_rework import BODY_PAL, quantize

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/Assassin/VideoMatch'
SOURCE=OUT/'source'
OLD=ROOT/'assets/Assassin/PixelRemake'
PREVIOUS=ROOT/'assets/Assassin/ModelLocked'


def cut_bodies(path,count,columns):
    source=np.asarray(Image.open(path).convert('RGBA'));rgb=source[:,:,:3]
    r,g,b=[rgb[:,:,i].astype(float) for i in range(3)]
    mask=(source[:,:,3]>128)&~((g>40)&(g>r*1.3+8)&(g>b*1.3+8))
    labels,_=ndi.label(mask,structure=np.ones((3,3)))
    areas=np.bincount(labels.ravel());boxes=ndi.find_objects(labels);objects=[]
    for index in np.flatnonzero(areas>900):
        if index:
            yy,xx=boxes[index-1]
            objects.append((int(index),(xx.start,yy.start,xx.stop,yy.stop)))
    assert len(objects)==count,(path.name,len(objects),count)
    objects.sort(key=lambda x:(x[1][1]+x[1][3])/2);ordered=[]
    for start in range(0,count,columns):
        ordered.extend(sorted(objects[start:start+columns],key=lambda x:x[1][0]))
    owner=np.zeros(labels.shape,dtype=np.int16)
    for index,(label,_) in enumerate(ordered): owner[labels==label]=index+1
    orphan=mask&(owner==0)&(areas[labels]>=10)
    if orphan.any():
        dist,near=ndi.distance_transform_edt(owner==0,return_indices=True)
        orphan &= dist<25
        owner[orphan]=owner[tuple(near)][orphan]
    items=[];gray=(rgb.min(axis=2)>=110)&(np.ptp(rgb,axis=2)<=45)
    for index in range(count):
        owned=owner==index+1;yy,xx=np.nonzero(owned)
        x0,y0,x1,y1=int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)
        soles=owned&gray&(np.arange(rgb.shape[0])[:,None]>=y0+(y1-y0)*.68)
        sy,sx=np.nonzero(soles);assert len(sy),(path.name,index,'missing sole')
        floor=int(sy.max());ax=float(sx.min()+sx.max())/2
        cut=rgb[y0:y1,x0:x1].copy()
        cut[:,:,1]=np.minimum(cut[:,:,1],np.maximum(cut[:,:,0],cut[:,:,2]))
        alpha=owned[y0:y1,x0:x1].astype('uint8')*255
        items.append(dict(image=Image.fromarray(np.dstack((cut,alpha))),
            box=[x0,y0,x1,y1],anchor=[ax,floor],source=path.name,
            source_index=index,body_height=floor-y0+1))
    return items


def build_effects(previous):
    vfx=previous['vfx'].copy()
    for spec in vfx.values(): shutil.copyfile(PREVIOUS/spec['sheet'],OUT/spec['sheet'])
    colors=[tuple(bytes.fromhex(c)) for c in ['3b081c','710d25','ab142d','d92239',
        'f43c48','ff675d','ffa06c','ffd393','fff1d6','ffffff']]
    pal=Image.new('P',(1,1));pal.putpalette([v for rgb in (colors*26)[:256] for v in rgb])
    fire_colors=colors+[(250,107,11),(255,155,32),(255,199,89)]
    fire_pal=Image.new('P',(1,1))
    fire_pal.putpalette([v for rgb in (fire_colors*20)[:256] for v in rgb])
    specs=[('slash_fx',('sweep_cut','rising_cut','cross_finish','flame_cut'),
        (0,256,512,768,1024),64),
        ('ability_fx',('spin_ring','red_eruption','thrown_dagger','sonic_blast'),
        (0,230,570,730,1024),96)]
    for source,names,edges,native_size in specs:
        src=Image.open(SOURCE/f'{source}.png').convert('RGBA');cw=src.width/6
        for row,name in enumerate(names):
            size=64 if name=='thrown_dagger' else native_size
            active_pal=fire_pal if name in ('flame_cut','thrown_dagger','sonic_blast') else pal
            y0,y1=edges[row:row+2];ground=name in ('red_eruption','sonic_blast')
            scale=(size-8)/max(cw,y1-y0);sheet=Image.new('RGBA',(size*6,size))
            for col in range(6):
                a=np.asarray(src.crop((round(col*cw),y0,round((col+1)*cw),y1))).copy()
                a[:,:,3]=np.where(a[:,:,3]>=160,255,0).astype('uint8')
                tile=Image.fromarray(a)
                ay=(525-y0 if name=='red_eruption' else 978-y0) if ground else (y1-y0)/2
                target_y=size-7 if ground else size/2
                coeff=(1/scale,0,cw/2-size/2/scale,0,1/scale,ay-target_y/scale)
                frame=quantize(tile.transform((size,size),Image.Transform.AFFINE,
                    coeff,Image.Resampling.NEAREST),active_pal)
                assert frame.getbbox(),(name,col,'empty effect')
                sheet.alpha_composite(frame,(col*size,0))
            sheet.save(OUT/'VFX'/f'{name}.png')
            vfx[name]={'sheet':f'VFX/{name}.png','frames':6,'cell_size':[size,size],
                'anchor':[size//2,size-7 if ground else size//2],
                'directional':name not in ('spin_ring','red_eruption','sonic_blast'),
                'scale':1 if name=='thrown_dagger' else 3 if ground or name=='spin_ring' else 2}
    return vfx


def build():
    (OUT/'sheets').mkdir(exist_ok=True);(OUT/'VFX').mkdir(exist_ok=True)
    idle=Image.open(OLD/'sheets/idle.png').convert('RGBA')
    neutral={d:[idle.crop((c*CELL,r*CELL,(c+1)*CELL,(r+1)*CELL))
        for c in (0,1)] for r,d in enumerate(DIRECTIONS)}
    soles={'down':87,'left':86,'right':87,'up':87}
    records=[];clips={};built={}
    def align(item,scale,facing,lift=0):
        ax,ay=item['anchor'];x0,y0,_,_=item['box'];target=soles[facing]-lift
        coeff=(1/scale,0,ax-x0-PIVOT[0]/scale,0,1/scale,ay-y0-target/scale)
        frame=quantize(item['image'].transform((CELL,CELL),Image.Transform.AFFINE,
            coeff,Image.Resampling.NEAREST),BODY_PAL)
        # Nearest-neighbor sampling can put the source sole one pixel above
        # its mathematical anchor. Correct the actual exported pixel floor.
        a=np.asarray(frame);gray=(a[:,:,:3].min(axis=2)>=100)&(np.ptp(a[:,:,:3],axis=2)<=45)
        ys=np.nonzero(gray&(a[:,:,3]>30)&(np.arange(CELL)[:,None]>=76-lift))[0]
        assert len(ys),(item['source'],item['source_index'],'exported sole')
        dy=target-int(ys.max());grounded=Image.new('RGBA',(CELL,CELL))
        grounded.alpha_composite(frame,(0,dy))
        return grounded
    def make_row(name,facing,items):
        scale=(BODY_HEIGHT-1)/items[0]['body_height'];frames=[]
        for col,item in enumerate(items):
            lift={5:10,6:17}.get(col,0) if name=='deaths_dance' else 0
            frame=align(item,scale,facing,lift)
            guard=not name.startswith('walk_') and col in (0,len(items)-1)
            if guard:frame=neutral[facing][int(col!=0)].copy()
            frames.append(frame)
            records.append({k:v for k,v in item.items() if k!='image'}|{
                'animation':name,'direction':facing,'frame':col,'scale':scale,
                'approved_guard':guard,'sole_y':soles[facing],'aerial_lift':lift})
        return frames,scale
    for prefix,source in [('attack_','attack'),('walk_attack_','moving')]:
        for step in (1,2,3):
            name=f'{prefix}{step}';raw=cut_bodies(SOURCE/f'{source}{step}.png',24,6)
            built[name]={};scales={}
            for r,d in enumerate(DIRECTIONS):
                built[name][d],scales[d]=make_row(name,d,raw[r*6:(r+1)*6])
            clips[name]={'sheet':f'sheets/{name}.png','frames_per_direction':6,
                'source':f'{source}{step}.png','scale_by_direction':scales}
            print(name,'packed',flush=True)
    for name in ('deaths_dance','sonic_stream'):
        built[name]={};scales={}
        for d in DIRECTIONS:
            built[name][d],scales[d]=make_row(name,d,cut_bodies(SOURCE/f'{name}_{d}.png',12,6))
        clips[name]={'sheet':f'sheets/{name}.png','frames_per_direction':12,'scale_by_direction':scales}
        print(name,'packed',flush=True)
    corrections=cut_bodies(SOURCE/'pose_corrections.png',6,3)
    for name,d,index,source_index,guard in [('sonic_stream','down',9,1,0),
        ('attack_2','up',1,3,2),('attack_2','up',2,4,2),('sonic_stream','up',5,5,2)]:
        built[name][d][index]=align(corrections[source_index],(BODY_HEIGHT-1)/corrections[guard]['body_height'],d)
        clips[name].setdefault('pose_corrections',{})[f'{d}:{index}']=source_index
    previous=json.loads((PREVIOUS/'manifest.json').read_text())
    clips['dash_attack']=previous['animations']['dash_attack']
    shutil.copyfile(PREVIOUS/'sheets/dash_attack.png',OUT/'sheets/dash_attack.png')
    metrics=[]
    for name,rows in built.items():
        count=len(rows['down']);sheet=Image.new('RGBA',(count*CELL,CELL*4))
        for r,d in enumerate(DIRECTIONS):
            for c,frame in enumerate(rows[d]):
                box=frame.getbbox()
                assert box and min(box[:2])>=3 and max(box[2:])<=CELL-3,(name,d,c,box)
                sheet.alpha_composite(frame,(c*CELL,r*CELL))
                metrics.append(dict(animation=name,direction=d,frame=c,bounds=box,
                    sha256=hashlib.sha256(frame.tobytes()).hexdigest()))
        sheet.save(OUT/'sheets'/f'{name}.png')
    manifest={'version':1,'character':'Sung Jinwoo','cell_size':[CELL,CELL],
        'pivot':list(PIVOT),'standing_height_px':BODY_HEIGHT,'sole_y_by_direction':soles,
        'display_size':[240,240],'draw_offset':[-10,-12],'direction_rows':DIRECTIONS,
        'palette':COLORS,'animations':clips,'vfx':build_effects(previous),
        'aliases':{'walk_attack':'walk_attack_1','run_attack':'walk_attack_1'},
        'q_motion':'advancing spin, aerial turn, ground strike, three red eruptions',
        'e_motion':'five cuts, backstep, dagger throw, one impact explosion',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.png')}}
    for filename,data in [('manifest',manifest),('frame_metrics',records),('packed_frame_metrics',metrics)]:
        (OUT/f'{filename}.json').write_text(json.dumps(data,indent=2)+'\n')
    qa=ROOT/'tests/artifacts/jinwoo';qa.mkdir(parents=True,exist_ok=True)
    for d in DIRECTIONS:
        board=Image.new('RGB',(1920,len(built)*200),'#202536');draw=ImageDraw.Draw(board)
        for row,(name,rows) in enumerate(built.items()):
            draw.text((5,row*200+2),name,fill='#e7e5e5')
            for col,frame in enumerate(rows[d]):
                pic=frame.crop((20,4,100,94)).resize((160,180),Image.Resampling.NEAREST)
                board.paste(pic,(col*160,row*200+20),pic)
        board.save(qa/f'video_match_{d}.png')
    print('Packed240 new poses, preserved24 dash-click poses,102 effects',flush=True)


if __name__=='__main__':
    import sys
    if '--effects-only' in sys.argv:
        m=json.loads((OUT/'manifest.json').read_text())
        m['vfx']=build_effects(json.loads((PREVIOUS/'manifest.json').read_text()))
        (OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    else:build()
