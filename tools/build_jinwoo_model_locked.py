"""Pack the approved Jinwoo model and newly authored attack poses.

Mechanical matte removal, slicing, palette mapping and alignment only.
No procedural body drawing or body-part compositing.
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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/Assassin/ModelLocked'
SOURCE = OUT / 'source'
OLD = ROOT / 'assets/Assassin/PixelRemake'
PREVIOUS = ROOT / 'assets/Assassin/DaggerRework'
SOURCES = {'attack_2':'attack2','attack_3':'attack3',
           'walk_attack_1':'moving1','walk_attack_2':'moving2',
           'walk_attack_3':'moving3','dash_attack':'dash_attack'}


def cut_bodies(path, count, columns):
    rgb = np.array(Image.open(path).convert('RGB'))
    r,g,b = [rgb[:,:,i].astype(float) for i in range(3)]
    green = (g>40) & (g>r*1.3+8) & (g>b*1.3+8)
    if green.mean() > .25:
        background = green
        # Remove exterior white margins while preserving pale boots/shirt.
        candidate = rgb.min(axis=2)>215
    else:
        # Flood the approved strip's gray matte, preserving enclosed navy.
        median = np.median(rgb[:30,:,:].reshape(-1,3),axis=0)
        candidate = np.linalg.norm(rgb.astype(float)-median,axis=2)<15
        background = np.zeros(candidate.shape,dtype=bool)
    seed = np.zeros(candidate.shape,dtype=bool)
    seed[0]=candidate[0]; seed[-1]=candidate[-1]
    seed[:,0]=candidate[:,0]; seed[:,-1]=candidate[:,-1]
    background |= ndi.binary_propagation(seed,mask=candidate)
    mask = ~background
    labels,_ = ndi.label(mask,structure=np.ones((3,3)))
    areas = np.bincount(labels.ravel())
    boxes = ndi.find_objects(labels)
    objects = []
    for index in np.flatnonzero(areas>900):
        if index:
            yy,xx = boxes[index-1]
            objects.append((int(index),(xx.start,yy.start,xx.stop,yy.stop)))
    assert len(objects)==count,(path.name,'connected bodies',len(objects))
    objects.sort(key=lambda x:(x[1][1]+x[1][3])/2)
    ordered = []
    for start in range(0,count,columns):
        ordered.extend(sorted(objects[start:start+columns],key=lambda x:x[1][0]))
    owner = np.zeros(labels.shape,dtype=np.int16)
    for index,(label,_) in enumerate(ordered):
        owner[labels==label]=index+1
    # Discard isolated matte noise; retain nearby detached real clusters.
    orphan = mask & (owner==0) & (areas[labels]>=10)
    if orphan.any():
        distance,near = ndi.distance_transform_edt(owner==0,return_indices=True)
        orphan &= distance<25
        owner[orphan]=owner[tuple(near)][orphan]
    items = []
    for index in range(count):
        owned = owner==index+1
        yy,xx = np.nonzero(owned)
        x0,y0,x1,y1 = int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)
        dark = owned & (rgb.max(axis=2)<65)
        floor = int(np.nonzero(dark)[0].max())
        band = dark[max(0,floor-max(4,round((floor-y0+1)*.10))):floor+1]
        sole_x = np.nonzero(band)[1]
        ax = float(sole_x.min()+sole_x.max())/2
        cut = rgb[y0:y1,x0:x1].copy()
        cut[:,:,1]=np.minimum(cut[:,:,1],np.maximum(cut[:,:,0],cut[:,:,2]))
        alpha = owned[y0:y1,x0:x1].astype('uint8')*255
        items.append(dict(image=Image.fromarray(np.dstack((cut,alpha))),
            box=[x0,y0,x1,y1],anchor=[ax,floor],source=path.name,
            source_index=index,body_height=floor-y0+1))
    return items


def build():
    (OUT/'sheets').mkdir(exist_ok=True)
    (OUT/'VFX').mkdir(exist_ok=True)
    idle = Image.open(OLD/'sheets/idle.png').convert('RGBA')
    neutral = {d:[idle.crop((c*CELL,r*CELL,(c+1)*CELL,(r+1)*CELL))
                  for c in (0,1)] for r,d in enumerate(DIRECTIONS)}
    records,clips,built = [],{},{}

    def sole_floor(frame):
        a = np.asarray(frame)
        gray = (a[:,:,:3].min(axis=2)>=100) & (np.ptp(a[:,:,:3],axis=2)<=45)
        sole = gray & (a[:,:,3]>30) & (np.arange(CELL)[:,None]>=76)
        ys = np.nonzero(sole)[0]
        assert len(ys),'No pale boot sole in the foot band'
        return int(ys.max())

    ground_soles = {d:sole_floor(neutral[d][0]) for d in DIRECTIONS}

    def align(item,scale,facing):
        ax,ay=item['anchor']; x0,y0,_,_=item['box']
        coeff=(1/scale,0,ax-x0-PIVOT[0]/scale,
               0,1/scale,ay-y0-PIVOT[1]/scale)
        frame=quantize(item['image'].transform((CELL,CELL),
            Image.Transform.AFFINE,coeff,Image.Resampling.NEAREST),BODY_PAL)
        # Foot-shadow thickness varies in generated art. Ground the actual
        # pale soles at the approved guard's sole level, without resizing.
        dy=ground_soles[facing]-sole_floor(frame)
        grounded=Image.new('RGBA',(CELL,CELL))
        grounded.alpha_composite(frame,(0,dy))
        return grounded

    def make_row(name,facing,items):
        ref=items[-1] if name=='dash_attack' else items[0]
        scale=BODY_HEIGHT/ref['body_height']
        frames=[]
        for col,item in enumerate(items):
            frame=align(item,scale,facing)
            guard=not name.startswith('walk_') and (col==len(items)-1 or (
                name!='dash_attack' and col==0))
            if guard: frame=neutral[facing][int(col!=0)].copy()
            frames.append(frame)
            records.append({k:v for k,v in item.items() if k!='image'} | {
                'animation':name,'direction':facing,'frame':col,'scale':scale,
                'approved_guard':guard,'sole_y':ground_soles[facing]})
        return frames,scale

    raw_basic={}
    other=cut_bodies(SOURCE/'attack1_other.png',18,6)
    right=cut_bodies(SOURCE/'approved_attack1_right.png',6,3)
    raw_basic['attack_1']=dict(zip(('down','left','up'),
        (other[0:6],other[6:12],other[12:18]))) | {'right':right}
    for name,source in SOURCES.items():
        raw=cut_bodies(SOURCE/(source+'.png'),24,6)
        raw_basic[name]={d:raw[r*6:(r+1)*6] for r,d in enumerate(DIRECTIONS)}
    raw_basic['dash_attack']['down']=cut_bodies(SOURCE/'dash_down_correction.png',6,3)
    moving=raw_basic['walk_attack_1']
    moving['left'][3],moving['right'][3]=moving['right'][3],moving['left'][3]
    for name,rows in raw_basic.items():
        built[name]={};scales={}
        for facing in DIRECTIONS:
            built[name][facing],scales[facing]=make_row(name,facing,rows[facing])
        clips[name]={'sheet':f'sheets/{name}.png','frames_per_direction':6,
            'scale_by_direction':scales,
            'sources':{d:rows[d][0]['source'] for d in DIRECTIONS}}
        print(name,24,'frames',flush=True)
    for name in ('deaths_dance','sonic_stream'):
        built[name]={};scales={}
        for facing in DIRECTIONS:
            raw=cut_bodies(SOURCE/f'{name}_{facing}.png',12,6)
            built[name][facing],scales[facing]=make_row(name,facing,raw)
        clips[name]={'sheet':f'sheets/{name}.png','frames_per_direction':12,
            'scale_by_direction':scales,
            'sources':{d:f'{name}_{d}.png' for d in DIRECTIONS}}
        print(name,48,'frames',flush=True)

    # Whole independently authored poses, with scale from their own guard.
    selections=[('deaths_dance','left',8,1),('deaths_dance','left',9,2),
        ('deaths_dance','left',10,3),('sonic_stream','left',4,5),
        ('sonic_stream','left',5,4),('sonic_stream','left',8,3),
        ('sonic_stream','up',3,1),('sonic_stream','up',5,2),
        ('sonic_stream','up',7,3),('deaths_dance','up',2,1),
        ('deaths_dance','up',8,4),('deaths_dance','up',6,5)]
    for facing in ('left','up'):
        raw=cut_bodies(SOURCE/f'{facing}_corrections.png',6,3)
        scale=BODY_HEIGHT/raw[0]['body_height']
        for name,d,index,source_index in selections:
            if d!=facing: continue
            item=raw[source_index]
            built[name][d][index]=align(item,scale,d)
            clips[name].setdefault('pose_selections',{})[f'{d}:{index}']=(
                f'{facing}_corrections.png:{source_index}')
            records.append({k:v for k,v in item.items() if k!='image'} | {
                'animation':name,'direction':d,'frame':index,'scale':scale,
                'correction':True,'approved_guard':False,'sole_y':ground_soles[d]})
    built['walk_attack_3']['up'][3]=built['attack_3']['up'][3].copy()
    clips['walk_attack_3']['pose_selections']={'up:3':'attack_3:up:3'}
    clips['walk_attack_1']['pose_selections']={
        'left:3':'moving1.png:15','right:3':'moving1.png:9'}
    metrics=[]
    for name,rows in built.items():
        count=len(rows['down'])
        sheet=Image.new('RGBA',(CELL*count,CELL*4))
        for r,d in enumerate(DIRECTIONS):
            for c,frame in enumerate(rows[d]):
                box=frame.getbbox()
                assert box and min(box[:2])>=3 and max(box[2:])<=CELL-3,(name,d,c,box)
                sheet.alpha_composite(frame,(c*CELL,r*CELL))
                metrics.append(dict(animation=name,direction=d,frame=c,
                    pixel_bounds=box,sha256=hashlib.sha256(frame.tobytes()).hexdigest()))
        sheet.save(OUT/'sheets'/f'{name}.png')
    vfx=json.loads((PREVIOUS/'manifest.json').read_text())['vfx']
    for spec in vfx.values():
        shutil.copyfile(PREVIOUS/spec['sheet'],OUT/spec['sheet'])
    manifest={'version':1,'character':'Sung Jinwoo','cell_size':[CELL,CELL],
        'pivot':list(PIVOT),'standing_height_px':BODY_HEIGHT,
        'sole_y_by_direction':ground_soles,'display_size':[240,240],
        'draw_offset':[-10,-12],'direction_rows':DIRECTIONS,
        'palette':COLORS,'animations':clips,
        'aliases':{'walk_attack':'walk_attack_1','run_attack':'walk_attack_1'},
        'vfx':vfx,'vfx_source':'../DaggerRework/VFX',
        'preserves':'PixelRemake idle, locomotion, hurt, death and portrait bytes',
        'approved_model':'source/approved_attack1_right.png',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.png')}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'frame_metrics.json').write_text(json.dumps(records,indent=2)+'\n')
    (OUT/'packed_frame_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    qa=ROOT/'tests/artifacts/jinwoo';qa.mkdir(parents=True,exist_ok=True)
    for d in DIRECTIONS:
        board=Image.new('RGB',(1920,len(built)*180),'#202536')
        draw=ImageDraw.Draw(board)
        for row,(name,rows) in enumerate(built.items()):
            draw.text((5,row*180+2),name,fill='#e7e5e5')
            for col,frame in enumerate(rows[d]):
                pic=frame.crop((20,15,100,95)).resize((160,160),Image.Resampling.NEAREST)
                board.paste(pic,(col*160,row*180+20),pic)
        board.save(qa/f'model_locked_{d}.png')
    print('Built',len(metrics),'body frames; retained 54 separate effects',flush=True)


if __name__=='__main__':
    build()
