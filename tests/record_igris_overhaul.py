"""Record a normal-speed cadence comparison and four-view attack playback.

Uses the real Enemy action clock, movement, damage events and VFX renderer.
Panels follow each boss so the complete sword remains visible. For a full
stage recording use verify_gameplay.py --record gameplay.mp4.
"""
import argparse
from bisect import bisect_right
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from entities import Enemy, COMMANDER_ACTIONS, Projectile
from igris_data import IGRIS_BANK, IGRIS_PIVOT, IGRIS_FRAME_ENDS, render_igris_frame

VIEWS = [('right',(1,0)),('left',(-1,0)),('down',(0,1)),('up',(0,-1))]
MOVES = [('light_combo','Twin Cut'),('overhead_slash','Rising Cleave'),
         ('ground_slam','Execution Plunge'),('run_attack','Advancing Sweep'),
         ('dash_attack','Dash Pierce'),('ranged_thrust','Blood Wave')]


def record(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    canvas = pygame.Surface((1280,720))
    font = pygame.font.Font(None,38)
    small = pygame.font.Font(None,26)
    heading = pygame.font.Font(None,46)
    writer = subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo',
        '-pixel_format','rgb24','-video_size','1280x720','-framerate','30','-i','-',
        '-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',
        '-threads','2','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)
    def write():
        writer.stdin.write(pygame.image.tobytes(canvas,'RGB'))
    run_rows = [[render_igris_frame(f) for f in row] for row in IGRIS_BANK.clips['Run'].frames]
    old_ends = (75,140,205,270,345,410,475,540)
    for tick in range(180):
        canvas.fill((22,24,32))
        canvas.blit(heading.render('Igris | Heavier footwork',True,(239,226,207)),(30,20))
        canvas.blit(small.render('Same running poses and travel speed. Slower steps, longer foot contact.',True,(166,169,180)),(32,66))
        for row,(label,ends) in enumerate((('Previous',old_ends),('Updated',IGRIS_FRAME_ENDS['run']))):
            floor = 344+row*315
            canvas.blit(font.render(label,True,(239,121,114) if row else (166,169,180)),(30,floor-225))
            idx=min(bisect_right(ends,tick*1000/30 % ends[-1]),7)
            for c,(direction,_) in enumerate(VIEWS):
                x=230+c*285
                pygame.draw.line(canvas,(51,55,68),(x-110,floor),(x+110,floor))
                frame=run_rows[IGRIS_BANK.directions.index(direction)][idx]
                canvas.blit(frame,(x-IGRIS_PIVOT[0],floor-IGRIS_PIVOT[1]))
                text=small.render(direction.title(),True,(162,166,178))
                canvas.blit(text,text.get_rect(center=(x,floor+24)))
        write()
    for action,label in MOVES:
        bosses=[]
        for direction,(dx,dy) in VIEWS:
            e=Enemy('blood_red_commander',850,630)
            e.is_boss=True
            e._commander_sequence=lambda action=action:(action,)
            e.move_direction=e.sprite_direction=direction
            target=(e.center()[0]+dx*190,e.center()[1]+dy*190)
            bosses.append((e,target,[]))
        for tick in range(90):
            canvas.fill((22,24,32))
            canvas.blit(heading.render('Igris | '+label,True,(239,226,207)),(30,18))
            canvas.blit(small.render('Four directions | Normal playback speed | Camera follows each sprite',True,(166,169,180)),(32,63))
            for i,(e,target,projectiles) in enumerate(bosses):
                phase=tick%45
                if phase==6:
                    dx,dy=VIEWS[i][1]
                    target=(e.center()[0]+dx*190,e.center()[1]+dy*190)
                    bosses[i]=(e,target,projectiles)
                    e._begin_attack(target,(0,0))
                def spawn(enemy,point,kind,damage_mult):
                    pos=enemy.feet() if kind=='igris_shockwave' else enemy.center()
                    projectiles.append(Projectile(*pos,*point,1,kind=kind,source=enemy))
                if e.is_committed:
                    e.update(1000/30,target,lambda *a,**k:True,spawn)
                else:
                    e.igris_effects.update(e,1000/30,None)
                panel=pygame.Surface((640,310))
                panel.fill((26,28,38))
                x,y=320,272
                pygame.draw.line(panel,(50,54,68),(70,y),(570,y))
                ox,oy=x-e.feet()[0],y-e.feet()[1]
                panel.blit(small.render(VIEWS[i][0].title(),True,(172,177,190)),(24,14))
                for p in projectiles:
                    p.update(1000/30)
                    if p.alive and p.behind_source:p.draw(panel,ox,oy)
                e.draw(panel,ox,oy)
                for p in projectiles:
                    if p.alive and not p.behind_source:p.draw(panel,ox,oy)
                projectiles[:]=[p for p in projectiles if p.alive]
                canvas.blit(panel,((i%2)*640,92+(i//2)*314))
            if tick==20:
                pygame.image.save(canvas,path.with_name(action+'_preview.png'))
            write()
    writer.stdin.close()
    assert writer.wait(timeout=30)==0
    print('Recorded 24 seconds: cadence comparison and six attacks in four directions.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    record(parser.parse_args().output)
