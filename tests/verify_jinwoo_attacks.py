"""Exercise LMB/Q/E through real stage input, animation, motion and VFX.

The controlled stage has no enemies and injects one 85ms hit-stop per move.
This isolates clock drift and facing errors; verify_jinwoo_gameplay.py covers
real enemy hits, interruptions, menus, campaign progression and defeat.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_gameplay import Harness, ROOT, key_event
import pygame
import gameplay
from game_data import ASSASSIN_ANIM_ROWS
from jinwoo_data import ATTACK_FRAME_MS, BANK, BANK_PATH, FRAME_STARTS, frame_at, duration
from progression import new_run_state

DIRECTIONS=('down','left','right','up')
KEYS=dict(zip(DIRECTIONS,(pygame.K_s,pygame.K_a,pygame.K_d,pygame.K_w)))
CASES=[(f'attack_{step}',d,mode) for d in DIRECTIONS
       for mode in ('standing','walking','sprinting') for step in (1,2,3)]
CASES += [(name,d,'standing') for d in DIRECTIONS
          for name in ('deaths_dance','sonic_stream','dash_attack')]
LABELS={'attack_1':'LMB 1 / Low Sweep','attack_2':'LMB 2 / Rising Twin Cut',
        'attack_3':'LMB 3 / Turning Cross-Cut','deaths_dance':'Q / Crimson Eruption',
        'sonic_stream':'E / 10-hit Crimson Flurry','dash_attack':'Dash + LMB / Blue Nightstep Cut'}


class Complete(Exception):
    pass


class AttackProbe(Harness):
    def __init__(self, rate, cases=CASES, record=None):
        super().__init__('attack_probe')
        self.rate=rate
        self.cases=list(cases)
        self.case=None
        self.results=[]
        self.writer=None
        self.record=record
        self.recorded_frames=0
        if record:
            assert rate==60
            record.parent.mkdir(parents=True,exist_ok=True)
            self.writer=subprocess.Popen(['ffmpeg','-y','-loglevel','error',
                '-f','rawvideo','-pixel_format','rgb24','-video_size','1280x880',
                '-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast',
                '-crf','19','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(record)],
                stdin=subprocess.PIPE)

    def tick(self,*_):
        self.now += 1000/self.rate
        return 1000/self.rate

    def get_time(self):
        return 1000/self.rate

    def setup_case(self):
        if not self.cases:
            raise Complete
        self.case=self.cases.pop(0)
        name,d,mode=self.case
        state=self.latest['state']
        state.update(current_recovery=0,last_combo_time=int(self.now),
            combo_index=int(name[-1])-1 if name.startswith('attack_') else 0,
            last_special_time=-100000,last_sonic_stream_time=-100000,
            dash_finished_at=-100000,hitstop=0,stamina=1000,
            invulnerable_until=0,stage_intro_until=0)
        # Enough room for full travel in each direction without hitting a wall.
        feet_y=1005 if d=='up' else 635 if d=='down' else 825
        self.latest['hero_pos'][:]=[1100 if d=='left' else 550,feet_y-166]
        self.latest['jinwoo_fx'].effects.clear()
        self.keys.held={KEYS[d]}
        if mode=='sprinting': self.keys.held.add(pygame.K_LSHIFT)
        self.prep=0
        self.started=None
        self.visited=set()
        self.beats=set()
        self.stop_injected=False
        self.freeze_samples=0
        self.attack_count=state['stats']['attacks']
        self.initial_pos=None
        self.last_clock=None
        self.last_hit=state['last_hit_time']
        self.cost_before=None
        self.cost_checked=False
        self.trace=[]
        self.eruption_checked=False
        self.flurry_layers=set()
        self.flurry_echo_seen=False

    def present(self,surface):
        self.latest=sys._getframe(1).f_locals
        self.frames+=1
        assert self.frames<22000,'probe timeout'
        if self.case is None:
            self.setup_case()
            return
        name,d,mode=self.case
        state=self.latest['state']; anim=self.latest['anim']
        action=state['jinwoo_action']
        if self.started is None:
            self.prep+=1
            if self.prep==1 and mode=='standing':
                self.keys.held=set()
            if action:
                assert action['profile']==name,(self.case,action)
                self.started=action['start']
            elif self.prep>5:
                raise AssertionError(('input did not start',self.case,self.prep))
        if self.started is not None:
            elapsed=state['jinwoo_clock']-self.started
            self.trace.append((elapsed,tuple(self.latest['hero_pos'])))
            if name=='sonic_stream':
                for fx in self.latest['jinwoo_fx'].effects:
                    if fx.get('skill')=='sonic_stream':
                        assert fx['facing']==d
                        self.flurry_layers.add((fx['strike'],fx['layer']))
                self.flurry_echo_seen |= any(s['life']==110 for s in self.latest['jinwoo_fx'].shadows)
            if elapsed<duration(name):
                assert action and action['profile']==name,(self.case,elapsed,action)
                assert anim.frame_idx==frame_at(name,elapsed),(self.case,elapsed,anim.frame_idx)
                assert self.latest['direction']==d,(self.case,self.latest['direction'])
                self.visited.add(anim.frame_idx)
                if name not in ('deaths_dance','sonic_stream'):
                    if state['last_hit_time'] != self.last_hit:
                        assert anim.frame_idx==3,(self.case,'LMB contact frame',anim.frame_idx)
                        assert ('contact',0) not in self.beats,'Duplicate queued hit'
                        self.beats.add(('contact',0))
                        self.last_hit=state['last_hit_time']
                skill=state.get(name)
                if skill:
                    if not self.cost_checked:
                        cost=52 if name=='deaths_dance' else 60
                        assert abs(self.cost_before-state['stamina']-cost)<.1
                        before=state['stamina']
                        self.latest['use_special']()
                        self.latest['use_sonic_stream']()
                        assert state['stamina']==before,'Active ability charged twice'
                        assert state['jinwoo_action']['profile']==name
                        self.cost_checked=True
                    assert skill['elapsed_ms']==elapsed
                    fields=('spin_done','eruption_done') if name=='deaths_dance' else ('hit_done',)
                    hit_frames=((2,3,4),(7,)) if name=='deaths_dance' else (tuple(range(2,12)),)
                    for field,indices in zip(fields,hit_frames):
                        for index in skill[field]:
                            beat=(field,index)
                            if beat not in self.beats:
                                assert anim.frame_idx==indices[index],(self.case,beat,anim.frame_idx,elapsed)
                                self.beats.add(beat)
                    if name=='deaths_dance' and skill['eruption_done'] and not self.eruption_checked:
                        fx=[f for f in self.latest['jinwoo_fx'].effects if f['name']=='red_eruption']
                        assert len(fx)==1 and skill['eruption_done']=={0}
                        dx,dy=skill['vec'];x,y=skill['landing_pos']
                        assert fx[0]['pos']==(x+dx*96,y+dy*96),'Q eruption off centerline'
                        self.eruption_checked=True
                    if name=='sonic_stream':
                        assert not any(f['name'] in ('thrown_dagger','sonic_blast') for f in self.latest['jinwoo_fx'].effects)
                        assert 'projectile' not in skill and 'throw_done' not in skill
                    travel_start=180 if name=='deaths_dance' else 45
                    if elapsed<travel_start:
                        assert self.latest['hero_pos']==self.initial_pos,(name,'wind-up gliding')
                first_beat=FRAME_STARTS[name][2 if name in ('deaths_dance','sonic_stream') else 3]
                if elapsed < first_beat:
                    cuts={'sweep_cut','rising_cut','cross_finish','flame_cut','spin_ring','blue_dash_cut'}
                    assert not any(fx['name'] in cuts for fx in self.latest['jinwoo_fx'].effects),(
                        self.case,'slash appeared before the contact pose')
                if not self.stop_injected and elapsed>=first_beat:
                    state['hitstop']=85
                    self.stop_injected=True
                if self.last_clock==state['jinwoo_clock']:
                    self.freeze_samples+=1
                self.last_clock=state['jinwoo_clock']
            else:
                self.keys.held=set()
            # Leave a short neutral pause in the exported playback.
            if elapsed>=duration(name)+(270 if self.record else 90):
                assert self.visited==set(range(len(ATTACK_FRAME_MS[name]))),(self.case,self.visited)
                assert self.freeze_samples>=1,(self.case,'hit-stop not exercised')
                assert state['jinwoo_action'] is None and not anim.locked
                assert anim.current=='idle',(self.case,'did not return to idle',anim.current)
                assert state['stats']['attacks']==self.attack_count+1
                assert len(self.beats)==(4 if name=='deaths_dance' else 10 if name=='sonic_stream' else 1)
                if name in ('deaths_dance','sonic_stream'):
                    vec={'down':(0,1),'left':(-1,0),'right':(1,0),'up':(0,-1)}[d]
                    displacement=sum((b-a)*v for a,b,v in zip(self.initial_pos,self.latest['hero_pos'],vec))
                    assert abs(displacement-(280 if name=='deaths_dance' else 250))<.01,(name,displacement)
                    if name=='sonic_stream':
                        steps=[sum((b-a)*v for a,b,v in zip(p0,p1,vec))
                            for (_,p0),(_,p1) in zip(self.trace,self.trace[1:])]
                        assert min(steps)>=-0.001,'E moved backward'
                        assert self.flurry_layers=={(i,layer) for i in range(10)
                            for layer in ('main','offhand','sparks')}|{(9,'finish'),(9,'flare')}
                        assert self.flurry_echo_seen,'E pose echoes never appeared'
                        assert not self.latest['jinwoo_fx'].effects and not self.latest['jinwoo_fx'].shadows,'E effects outlived recovery'
                    else:
                        assert self.eruption_checked
                    before=state['stamina']
                    self.latest['use_special' if name=='deaths_dance' else 'use_sonic_stream']()
                    assert state['stamina']==before and state['jinwoo_action'] is None,'Cooldown bypass'
                self.results.append(dict(name=name,direction=d,mode=mode,
                    frames=sorted(self.visited),damage_beats=len(self.beats),
                    paused_frames=self.freeze_samples,rate=self.rate))
                self.case=None
        if self.writer and self.frames%2==0:
            self.write_preview(surface)

    def events(self):
        if self.case is None or self.started is not None:
            return []
        name,d,mode=self.case
        if self.prep==2:
            self.initial_pos=list(self.latest['hero_pos'])
            self.cost_before=self.latest['state']['stamina']
            if name in ('deaths_dance','sonic_stream','dash_attack'):
                key={'deaths_dance':pygame.K_q,'sonic_stream':pygame.K_e,'dash_attack':pygame.K_SPACE}[name]
                return [key_event(key)]
            return [pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(0,0))]
        if self.prep==3 and name=='dash_attack':
            return [pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(0,0))]
        return []

    def write_preview(self,surface):
        case=self.case or (self.results[-1]['name'],self.results[-1]['direction'],self.results[-1]['mode'])
        name,d,mode=case
        canvas=pygame.Surface((1280,880))
        canvas.fill((17,21,31))
        canvas.blit(surface,(0,100),pygame.Rect(360,300,1280,780))
        font=pygame.font.SysFont('DejaVu Sans',26,bold=True)
        small=pygame.font.SysFont('DejaVu Sans',18)
        canvas.blit(font.render(LABELS[name],True,(242,237,230)),(25,15))
        canvas.blit(small.render(f'{d.upper()}  /  {mode.upper()}  /  normal speed · actual game pixels',True,(168,188,212)),(26,58))
        self.writer.stdin.write(pygame.image.tobytes(canvas,'RGB'))
        self.recorded_frames+=1


def run(record=None):
    reports=[]
    for rate in (30,60,144):
        with patch.object(gameplay,'spawn_enemies',return_value=[]), AttackProbe(rate) as h:
            try:
                gameplay.stage_screen('Assassin','Jinwoo',2,new_run_state())
            except Complete:
                pass
            assert len(h.results)==len(CASES)
            reports.extend(h.results)
        print('PASS',rate,'FPS:',len(CASES),'directional action cases',flush=True)
    for name,spec in BANK['vfx'].items():
        im=pygame.image.load(str(BANK_PATH/spec['sheet']))
        w,h=spec['cell_size']
        assert im.get_size()==(w*6,h)
        hashes=set()
        for i in range(6):
            f=im.subsurface((i*w,0,w,h))
            assert f.get_bounding_rect().width>0
            hashes.add(hashlib.sha256(pygame.image.tobytes(f,'RGBA')).hexdigest())
        assert len(hashes)==6,(name,'duplicate effect frames')
    report=dict(status='passed',action_cases=len(reports),vfx_frames=sum(v["frames"] for v in BANK["vfx"].values()),
        rates=[30,60,144],checks=[
            'Real LMB/Q/E and dash-click input, all four facings, three standing/walking/sprinting combo attacks',
            'Each authored pose appears, every skill hit coincides with its exact contact pose',
            'No visible slash during the initial held wind-up; trails begin at contact',
            'Injected 85ms hit-stop pauses body, skill event clock and pixel effects together',
            'Q/E neutral wind-up remains planted; every action unlocks and returns to idle',
            'Q travels 280px with one eruption exactly 96px forward; E enters 250px with no backward step, throw or explosion',
            'Each input starts one attack; Q/E execute four/ten damage beats once',
            'Each E emits 21 directional slash layers, ten forward spark bursts, one finishing flash and short pose echoes; all clear after recovery',
            'Nineteen six-frame effects are nonempty and unique within their animation'],cases=reports)
    (ROOT/'tests/jinwoo_attack_qa.json').write_text(json.dumps(report,indent=2)+'\n')
    if record:
        record_preview(record)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))


def record_preview(record):
    # A concise directional showcase; the full 144-case report is separate.
    clips=[(f'attack_{i}','right','standing') for i in (1,2,3)]
    clips += [(f'attack_{i}','left','walking') for i in (1,2,3)]
    clips += [(f'attack_{i}','right','sprinting') for i in (1,2,3)]
    clips += [('dash_attack',d,'standing') for d in DIRECTIONS]
    clips += [(n,d,'standing') for d in DIRECTIONS for n in ('deaths_dance','sonic_stream')]
    with patch.object(gameplay,'spawn_enemies',return_value=[]), AttackProbe(60,clips,record) as h:
        try: gameplay.stage_screen('Assassin','Jinwoo',2,new_run_state())
        except Complete: pass
        assert len(h.results)==len(clips)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--record',type=Path)
    parser.add_argument('--record-only',action='store_true')
    args=parser.parse_args()
    if args.record_only:
        if not args.record: parser.error('--record-only requires --record')
        record_preview(args.record)
    else:
        run(args.record)
