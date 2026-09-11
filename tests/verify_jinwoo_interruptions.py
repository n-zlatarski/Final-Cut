"""Verify interrupted poses cannot leave delayed skill hits behind."""
import json
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_gameplay import Harness,ROOT
from jinwoo_data import duration
import gameplay
from progression import new_run_state

class Complete(Exception):pass
class Probe(Harness):
    def __init__(self):
        super().__init__('interruptions');self.phase=0;self.checks=[]
    def events(self):return []
    def present(self,surface):
        self.latest=sys._getframe(1).f_locals;self.frames+=1
        assert self.frames<900,'timeout'
        s=self.latest['state'];t=s['jinwoo_clock']
        if self.phase==0:
            self.latest['request_attack'](False,False)
            assert s['pending_hits'] and s['jinwoo_action']
            assert self.latest['hurt_hero'](1)
            assert not s['pending_hits'] and s['jinwoo_action'] is None
            self.hit_time=s['last_hit_time'];self.mark=t;self.phase=1
        elif self.phase==1 and t-self.mark>=550:
            assert s['last_hit_time']==self.hit_time
            self.checks.append('Hurt cancels an unlanded LMB hit and its pose')
            self.latest['request_attack'](False,False);assert s['pending_hits']
            self.latest['use_special']()
            assert s['deaths_dance'] and not s['pending_hits']
            self.checks.append('Q replaces LMB wind-up without an orphan hit');self.phase=2
        elif self.phase==2 and s['deaths_dance']['elapsed_ms']>=duration('deaths_dance')-80:
            assert self.latest['hurt_hero'](1)
            assert s['deaths_dance'] is None and s['jinwoo_action'] is None
            assert self.latest['anim'].current=='hurt'
            self.checks.append('Q yields to Hurt during vulnerable recovery')
            self.mark=t;self.phase=3
        elif self.phase==3 and t-self.mark>=550:
            self.latest['use_sonic_stream']();assert s['sonic_stream'];self.phase=4
        elif self.phase==4 and s['sonic_stream']['elapsed_ms']>=235:
            assert len(s['sonic_stream']['hit_done'])==2
            s['invulnerable_until']=0;assert self.latest['hurt_hero'](1)
            assert s['sonic_stream'] is None and s['jinwoo_action'] is None
            assert not self.latest['jinwoo_fx'].effects
            self.hit_time=s['last_hit_time'];self.mark=t;self.phase=5
        elif self.phase==5 and t-self.mark>=550:
            assert s['last_hit_time']==self.hit_time and not s['pending_hits']
            self.checks.append('Interrupting the E flurry suppresses all remaining cuts and effects')
            s['last_special_time']=-100000;s['stamina']=1000
            self.latest['use_special']();self.phase=6
        elif self.phase==6 and s['deaths_dance']['elapsed_ms']>=880:
            assert not s['deaths_dance']['eruption_done']
            s['invulnerable_until']=0;assert self.latest['hurt_hero'](1)
            self.hit_time=s['last_hit_time'];self.mark=t;self.phase=7
        elif self.phase==7 and t-self.mark>=550:
            assert s['last_hit_time']==self.hit_time and s['deaths_dance'] is None
            assert not self.latest['jinwoo_fx'].effects
            self.checks.append('Interrupting Q before landing suppresses its single eruption')
            raise Complete

if __name__=='__main__':
    with patch.object(gameplay,'spawn_enemies',return_value=[]),Probe() as p:
        try:gameplay.stage_screen('Assassin','Jinwoo',2,new_run_state())
        except Complete:pass
        assert len(p.checks)==5
        report=dict(status='passed',checks=p.checks,frames=p.frames,
            conditions='Real stage helpers, empty room; invulnerability explicitly cleared only for forced mid-skill interruption checks')
        (ROOT/'tests/jinwoo_interruption_qa.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
