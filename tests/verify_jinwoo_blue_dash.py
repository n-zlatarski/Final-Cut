"""Real-stage dash FX regression: directions, walls, lifetime and body safety."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_gameplay import Harness,ROOT,key_event
from verify_jinwoo_attacks import AttackProbe,LABELS
import pygame
import gameplay
from game_data import ASSASSIN_ANIM_ROWS
from progression import new_run_state

DIRECTIONS=('down','left','right','up')
KEYS=dict(zip(DIRECTIONS,(pygame.K_s,pygame.K_a,pygame.K_d,pygame.K_w)))
LABELS['dash']='SPACE / Blue Shadow Dash'
class Complete(Exception):pass
class Probe(Harness):
    def __init__(self,rate,record=None):
        super().__init__('blue_dash');self.rate=rate;self.record=record
        self.cases=[('dash',d,m) for d in DIRECTIONS for m in (('open',) if record else ('open','wall'))]
        self.case=None;self.results=[];self.recorded_frames=0
        if record:
            record.parent.mkdir(parents=True,exist_ok=True)
            self.writer=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
                '-video_size','1280x880','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast',
                '-crf','19','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(record)],stdin=subprocess.PIPE)
    def tick(self,*_):self.now+=1000/self.rate;return 1000/self.rate
    def get_time(self):return 1000/self.rate
    def events(self):
        if self.case and self.mark is None and self.prep==2:
            self.mark=self.latest['state']['jinwoo_clock']
            return [key_event(pygame.K_SPACE)]
        return []
    def setup(self):
        if not self.cases:raise Complete
        self.case=self.cases.pop(0);_,d,mode=self.case
        s=self.latest['state'];s.update(stamina=1000,hitstop=0,stage_intro_until=0)
        pos=self.latest['hero_pos'];feet=1005 if d=='up' else 635 if d=='down' else 825
        pos[:]=[1100 if d=='left' else 550,feet-166]
        if mode=='wall':
            if d in ('left','right'):pos[0]=0 if d=='left' else self.latest['STAGE_EXIT_X']
            else:pos[1]=(self.latest['TOP_BORDER_Y'] if d=='up' else gameplay.HEIGHT)-166
        self.latest['jinwoo_fx'].clear();self.keys.held={KEYS[d]}
        self.prep=0;self.mark=None;self.seen=set();self.max_shadows=0;self.blue_seen=False
        self.frozen=0;self.last_clock=None;self.injected=False
    def present(self,surface):
        self.latest=sys._getframe(1).f_locals;self.frames+=1;assert self.frames<6000
        if self.case is None:self.setup();return
        self.prep+=1
        if self.prep==1:self.keys.held=set()
        if self.mark is not None:
            s=self.latest['state'];fx=self.latest['jinwoo_fx'];t=s['jinwoo_clock']-self.mark
            self.seen.update(f['name'] for f in fx.effects)
            self.max_shadows=max(self.max_shadows,len(fx.shadows))
            self.blue_seen |= self.latest['blue_dash']
            if not self.record and not self.injected and t>=95:
                s['hitstop']=85;self.injected=True
            if self.last_clock==s['jinwoo_clock']:self.frozen+=1
            self.last_clock=s['jinwoo_clock']
            if t>=650:
                assert not fx.effects and not fx.shadows,'Dash FX outlived their move'
                assert not s['dashing'] and not self.latest['blue_dash']
            if t>=900:
                _,d,mode=self.case
                assert self.blue_seen and 'blue_dash_burst' in self.seen
                if mode=='open':
                    assert 'blue_dash_stream' in self.seen and self.max_shadows>=1
                else:
                    assert 'blue_dash_stream' not in self.seen and self.max_shadows==0,'Wall emitted false movement trail'
                if not self.record:assert self.frozen>=1
                self.results.append(dict(name='dash',direction=d,mode=mode,rate=self.rate,
                    effects=sorted(self.seen),max_afterimages=self.max_shadows,paused_frames=self.frozen))
                self.case=None
        if self.writer and self.frames%2==0:AttackProbe.write_preview(self,surface)

def run(record=None,record_only=False):
    frames=[f for name in ('dash','dash_attack') for row in ASSASSIN_ANIM_ROWS[name] for f in row]
    before=[hashlib.sha256(pygame.image.tobytes(f,'RGBA')).digest() for f in frames]
    cases=[]
    if not record_only:
        for rate in (30,60,144):
            with patch.object(gameplay,'spawn_enemies',return_value=[]),Probe(rate) as h:
                try:gameplay.stage_screen('Assassin','Jinwoo',2,new_run_state())
                except Complete:pass
                assert len(h.results)==8;cases.extend(h.results)
        report=dict(status='passed',cases=cases,checks=[
            'Blue body tint, launch/landing bursts, slipstreams and sampled afterimages in all four directions',
            'Stationary wall dashes emit no movement trails or afterimages',
            'Effects expire after the move; simulation-clock hit-stop pauses their lifetimes',
            'Original dash and dash-attack frame bytes remain unchanged'])
        (ROOT/'tests/jinwoo_blue_dash_qa.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS',len(cases),'dash cases at 30,60,144 FPS')
    if record:
        with patch.object(gameplay,'spawn_enemies',return_value=[]),Probe(60,record) as h:
            try:gameplay.stage_screen('Assassin','Jinwoo',2,new_run_state())
            except Complete:pass
            assert len(h.results)==4
    assert before==[hashlib.sha256(pygame.image.tobytes(f,'RGBA')).digest() for f in frames]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record',type=Path);p.add_argument('--record-only',action='store_true')
    a=p.parse_args();run(a.record,a.record_only)
