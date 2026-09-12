"""Generated pixel VFX, sampled world anchors and the attack simulation clock."""
import math
import pygame
from jinwoo_data import BANK, BANK_PATH

VECTORS = {'right': (1,0), 'left': (-1,0), 'up': (0,-1), 'down': (0,1)}


class JinwooVFX:
    def __init__(self):
        self.frames = {}
        self.cache = {}
        self.effects = []
        self.shadows = []
        self.last_shadow = -10000
        self.last_trail = None
        self.dash_in_progress = False
        self.dash_origin = None
        self.last_blue_sample = None
        self.body_cache = {}
        for name, spec in BANK['vfx'].items():
            sheet = pygame.image.load(str(BANK_PATH / spec['sheet'])).convert_alpha()
            w,h = spec['cell_size']
            self.frames[name] = [sheet.subsurface((i*w,0,w,h)).copy()
                                 for i in range(spec['frames'])]
        self.frames['waist_cut'] = self.frames['lunge_streak']
        # Exact reflection of paired streaks for the descending dagger rake.
        self.frames['twin_rake'] = [pygame.transform.flip(f,False,True)
                                    for f in self.frames['stabbing_trail']]

    def add(self, name, pos, facing, now, *, life=210, start=None,
            follow_ms=0, offset=(0,0), peak=False, end_pos=None, heading=None, scale=None):
        effect=dict(name=name, pos=tuple(pos), facing=facing,
            start=now if start is None else start, life=life,
            follow_until=now+follow_ms if follow_ms else None,
            offset=offset, peak=peak, origin=tuple(pos), end_pos=end_pos, heading=heading, scale=scale)
        self.effects.append(effect)
        return effect

    def cut(self, name, center, facing, now, *, start=None, follow_ms=0,
            life=210, peak=False, scale=None):
        dx,dy=VECTORS[facing]
        # Match the waist cut, higher backhand and descending rake.
        lift={'quick_arc':-20, 'cross_slash':-5, 'dance_cut':0,
              'stabbing_trail':0, 'lunge_streak':10, 'waist_cut':3,
              'twin_rake':25, 'sweep_cut':8, 'rising_cut':-24,
              'cross_finish':0, 'flame_cut':-5, 'blue_dash_cut':-5}.get(name,-10)
        offset=(dx*36, dy*18+lift)
        if name == 'blue_dash_cut':
            offset=(dx*48, dy*38+lift)
        if name=='twin_rake' and facing=='up':
            # Away-facing arms are in front of the torso: draw the rake
            # behind the coat, while front/side contacts stay near the hands.
            offset=(0,-30)
        return self.add(name,(center[0]+offset[0],center[1]+offset[1]),facing,now,
                 life=life,start=start,follow_ms=follow_ms,offset=offset,peak=peak,scale=scale)

    def flurry_cut(self, index, center, facing, now, *, start, last=False):
        """Paired directional dagger trails, with a larger finishing cross."""
        names=('rising_cut','flame_cut','sweep_cut','flame_cut','cross_finish',
               'sweep_cut','rising_cut','cross_finish','rising_cut','cross_finish')
        primary=self.cut(names[index],center,facing,now,start=start,
            life=180 if last else 105,peak=True,scale=3 if last else 2)
        primary.update(skill='sonic_stream',strike=index,layer='main')
        dx,dy=VECTORS[facing]
        side=-14 if index%2 else 14
        point=(center[0]+dx*46-dy*side,center[1]+dy*30+dx*side-10)
        secondary=self.add('sweep_cut' if index%2 else 'rising_cut',point,facing,now,
            start=start+20,life=140 if last else 95,peak=True,scale=2 if last else 1)
        secondary.update(skill='sonic_stream',strike=index,layer='offhand')
        spark_point=(center[0]+dx*70-dy*side*.6,
                     center[1]+dy*52+dx*side*.6-8)
        sparks=self.add('flurry_sparks',spark_point,facing,now,
            start=start+10,life=180 if last else 144)
        sparks.update(skill='sonic_stream',strike=index,layer='sparks',finisher=last)
        if last:
            finish=self.add('flame_cut',(center[0]+dx*64,center[1]+dy*42-10),facing,now,
                start=start+35,life=135,peak=True,scale=2)
            finish.update(skill='sonic_stream',strike=index,layer='finish')
            flare=self.add('contact',(center[0]+dx*84,center[1]+dy*58-8),facing,now,
                start=start+12,life=130,peak=True,scale=2)
            flare.update(skill='sonic_stream',strike=index,layer='flare')

    def _draw_flurry_sparks(self, surface, fx, elapsed, ox, oy):
        """Short forward fans, drawn on a native pixel grid then doubled."""
        tile=pygame.Surface((96,96),pygame.SRCALPHA)
        dx,dy=VECTORS[fx['facing']]
        angles=((-1.15,-.85,-.55,-.25,0,.25,.55,.85,1.15)
                if fx['finisher'] else (-1,-.48,.08,.55,1))
        palette=((255,230,189),(255,152,125),(240,69,80),(168,30,55))
        t=elapsed/fx['life']
        for i,angle in enumerate(angles):
            delay=(i%3)*.06
            progress=(t-delay)/(1-delay)
            if progress<0 or progress>=1:
                continue
            # A repeatable slight variation keeps the ten bursts distinct.
            angle+=(fx['strike']%3-1)*.1
            forward,side=math.cos(angle),math.sin(angle)
            vx,vy=dx*forward-dy*side,dy*forward+dx*side
            radius=2+(14+(i%3)*4)*progress
            tail=max(1,round(5*(1-progress)))
            head=(round(48+vx*radius),round(48+vy*radius*.72))
            end=(round(48+vx*max(0,radius-tail)),
                 round(48+vy*max(0,radius-tail)*.72))
            color=palette[min(3,int(progress*4))]
            pygame.draw.line(tile,color,end,head,1)
            if progress<.45:
                pygame.draw.rect(tile,palette[0],(*head,2,1))
        frame=pygame.transform.scale(tile,(192,192))
        surface.blit(frame,(round(fx['pos'][0]+ox-96),round(fx['pos'][1]+oy-96)))

    def sample_shadow(self, frame, pos, now, color, *, interval=75, life=225, opacity=90):
        """Snapshot an actual pose at its world position, without sliding it."""
        if now-self.last_shadow<interval:
            return
        self.last_shadow=now
        img=pygame.mask.from_surface(frame).to_surface(
            setcolor=(*color,opacity),unsetcolor=(0,0,0,0))
        self.shadows.append(dict(image=img,pos=tuple(pos),start=now,life=life))

    def clear(self):
        self.effects.clear()
        self.shadows.clear()
        self.last_trail = None
        self.last_blue_sample = None
        self.dash_in_progress = False
        self.dash_origin = None

    def begin_dash(self, feet, facing, now):
        self.dash_in_progress = True
        self.dash_origin = tuple(feet)
        self.last_trail = (now, tuple(feet))
        self.last_blue_sample = (now, tuple(feet))
        self.add('blue_dash_burst', feet, facing, now, life=250)

    def blue_layers(self, frame):
        """Temporary lighting on the real pose; source frames stay unchanged."""
        if frame not in self.body_cache:
            tinted = frame.copy()
            tinted.fill((70, 135, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
            tinted.fill((12, 40, 90, 0), special_flags=pygame.BLEND_RGBA_ADD)
            edge = pygame.mask.from_surface(frame).to_surface(
                setcolor=(66, 194, 255, 255), unsetcolor=(0, 0, 0, 0))
            self.body_cache[frame] = (tinted, edge)
        return self.body_cache[frame]

    def draw_blue_body(self, surface, frame, pos, strength=1.0):
        tinted, edge = self.blue_layers(frame)
        edge.set_alpha(round(100 * strength))
        x, y = pos
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surface.blit(edge, (x+dx, y+dy))
        surface.blit(frame, pos)
        tinted.set_alpha(round(195 * strength))
        surface.blit(tinted, pos)

    def sample_blue_shadow(self, frame, pos, feet, now):
        if self.last_blue_sample is None:
            self.last_blue_sample = (now, tuple(feet))
            return
        when, where = self.last_blue_sample
        if now-when < 40 or math.dist(feet, where) < 10:
            return
        self.last_blue_sample = (now, tuple(feet))
        tinted, _ = self.blue_layers(frame)
        image = tinted.copy()
        image.set_alpha(255)
        self.shadows.append(dict(image=image, pos=tuple(pos), start=now, life=210, opacity=125))

    def update(self, now, center, feet, facing, dash_active=False):
        self.effects[:] = [f for f in self.effects if now-f['start'] < f['life']]
        self.shadows[:]=[s for s in self.shadows if now-s['start']<s['life']]
        for f in self.effects:
            if f['end_pos'] is not None:
                t=max(0,min(1,(now-f['start'])/f['life']))
                f['pos']=tuple(a+(b-a)*t for a,b in zip(f['origin'],f['end_pos']))
            if f['follow_until'] is not None:
                f['pos']=(center[0]+f['offset'][0],center[1]+f['offset'][1])
                if now >= f['follow_until']:
                    f['follow_until']=None
        # Emit only from actual traversed world positions. No displaced copies
        # of today's pose, and no wake when a wall prevents movement.
        if not dash_active:
            if self.dash_in_progress and math.dist(feet, self.dash_origin) >= 10:
                self.add('blue_dash_burst', feet, facing, now, life=220)
            self.dash_in_progress = False
            self.last_trail=None
            self.last_blue_sample = None
        elif self.last_trail is None:
            self.begin_dash(feet, facing, now)
        elif (now-self.last_trail[0] >= 45 and
              math.dist(feet,self.last_trail[1]) >= 8):
            dx,dy=VECTORS[facing]
            self.add('blue_dash_stream', (center[0]-dx*28, center[1]-dy*20),
                     facing, now, life=170)
            self.add('blue_wake',(feet[0]-dx*36,feet[1]-dy*28-16),
                     facing,now,life=190)
            self.last_trail=(now,feet)

    def texture(self, name, index, facing, heading=None, scale=None):
        key=(name,index,facing,heading,scale)
        if key in self.cache:
            return self.cache[key]
        frame=self.frames[name][index]
        # Integer scales and cardinal transforms preserve crisp pixels.
        spec=BANK['vfx'].get(name,{})
        scale=scale if scale is not None else spec.get('scale',1 if name=='contact' else 2)
        directional=spec.get('directional',True)
        if heading is not None:
            frame=pygame.transform.rotate(frame,heading)
        elif directional and facing=='left':
            frame=pygame.transform.flip(frame,True,False)
        elif directional and facing in ('up','down'):
            frame=pygame.transform.rotate(frame,90 if facing=='up' else -90)
            # Ground-plane foreshortening, performed at native scale.
            frame=pygame.transform.scale(frame,(frame.get_width(),round(frame.get_height()*2/3)))
        img=pygame.transform.scale(frame,(frame.get_width()*scale,frame.get_height()*scale))
        anchor=(tuple(round(v*scale) for v in spec['anchor'])
                if not directional and 'anchor' in spec else
                (img.get_width()//2,img.get_height()//2))
        self.cache[key]=(img,anchor)
        return img,anchor

    def draw(self, surface, now, hero_center, ox=0, oy=0, *, behind=False):
        if behind:
            for s in self.shadows:
                img=s['image'].copy()
                img.set_alpha(round(s.get('opacity',255)*(1-(now-s['start'])/s['life'])))
                surface.blit(img,(round(s['pos'][0]+ox),round(s['pos'][1]+oy)))
        for fx in self.effects:
            elapsed=now-fx['start']
            if elapsed<0 or elapsed>=fx['life']:
                continue
            ground=fx['name']=='red_eruption' or BANK['vfx'].get(fx['name'],{}).get('ground',False)
            is_behind=fx['pos'][1]<hero_center[1]+(54 if ground else -6)
            if fx['name'] in ('blue_dash_stream', 'blue_dash_burst'):
                is_behind=True
            ring=fx['name']=='spin_ring'
            if not ring and is_behind != behind:
                continue
            if fx['name']=='flurry_sparks':
                self._draw_flurry_sparks(surface,fx,elapsed,ox,oy)
                continue
            t=elapsed/fx['life']
            index=min(5,(2+int(t*4)) if fx['peak'] else int(t*6))
            frame,anchor=self.texture(fx['name'],index,fx['facing'],fx['heading'],fx.get('scale'))
            x,y=round(fx['pos'][0]+ox-anchor[0]),round(fx['pos'][1]+oy-anchor[1])
            if ring:
                half=frame.get_height()//2
                area=pygame.Rect(0,0 if behind else half,frame.get_width(),half)
                surface.blit(frame,(x,y+area.y),area)
            else:
                surface.blit(frame,(x,y))
