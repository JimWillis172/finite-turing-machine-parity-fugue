#!/usr/bin/env python3
import argparse, csv, os, struct
from dataclasses import dataclass
from typing import Dict, Tuple
from collections import deque

import pygame

# ----------------------------
# Data
# ----------------------------
BG_COLOR = (128, 128, 128)
TEAL     = (0, 70, 70)

@dataclass(frozen=True)
class Rule:
    write: int
    move: int
    next_pc: int

@dataclass
class MachineState:
    tape: list
    i: int = 0
    pc: int = 1
    cycle: int = 0

@dataclass
class RuntimeConfig:
    fps_target: int = 60
    scale: int = 1
#    draw_alpha: int = 40

# ----------------------------
# Helpers
# ----------------------------

def bit_to_i16(bit: bool) -> int:
    return 12000 if bit else 0

def load_program(csv_path: str) -> Dict[Tuple[int, int], Rule]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing program file: {csv_path}")

    program: Dict[Tuple[int, int], Rule] = {}
    pcs = set()

    with open(csv_path, newline="") as f:
        rdr = csv.DictReader(f)
        required = {"pc", "read", "write", "move", "next_pc"}
        if not required.issubset(set(rdr.fieldnames or [])):
            raise ValueError(f"program.csv must have columns: {sorted(required)}")

        for row in rdr:
            pc = int(row["pc"])
            read = int(row["read"])
            write = int(row["write"])
            mv = row["move"].strip().upper()
            next_pc = int(row["next_pc"])

            move = -1 if mv == "L" else (1 if mv == "R" else (0 if mv == "S" else None))
            if move is None:
                raise ValueError(f"Bad move {mv!r} in row {row}")
            if write not in (0, 1, 2):
                raise ValueError(f"write must be 0/1/(2), got {write}")

            program[(pc, read)] = Rule(write=write, move=move, next_pc=next_pc)
            pcs.add(pc)

    for pc in pcs:
        for read in (0, 1):
            if (pc, read) not in program:
                raise ValueError(f"Missing rule for pc={pc}, read={read}")

    return program

def reset_machine(state: MachineState, N: int) -> None:
    state.tape[:] = [0] * N
    state.i = 0
    state.pc = 1
    state.cycle = 0
    # optional seed/defect
    state.tape[N // 4] = 1

# ----------------------------
# Main
# ----------------------------

def run_ftmp_forever(N: int, fps: int, audio_hz: int, program_path: str) -> None:
    cfg = RuntimeConfig(fps_target=fps)
    program = load_program(program_path)

    # --- pygame init ---
    pygame.init()
    # pygame.mixer.pre_init(audio_hz, size=-16, channels=2, buffer=2048)
    pygame.mixer.pre_init(audio_hz, size=-16, channels=2, buffer=4096)

    pygame.mixer.init()

    scale = cfg.scale
    canvas = pygame.Surface((N * scale, N * scale), pygame.SRCALPHA)
    screen = pygame.display.set_mode((N * scale, N * scale))
    clock = pygame.time.Clock()
    chan = pygame.mixer.Channel(0)

    # --- knobs / controls ---
    delay_samples = 0          # start with intrinsic machine delay only
    MIN_DELAY = 0
    MAX_DELAY = audio_hz       # ~1 second max
    delay_line = deque([0] * max(1, delay_samples), maxlen=max(1, delay_samples))

    draw_alpha = 6      # ink brightness (0..255-ish)
    decay_alpha = 2     # fade rate per frame (0..50-ish)


    # chunk timing in ms => stable feel across audio_hz
    # CHUNK_MS = 30              # 20–60 feels good
    CHUNK_MS = 60

    CHUNK_FRAMES = max(256, int(audio_hz * CHUNK_MS / 1000))
    CHUNK_BYTES = CHUNK_FRAMES * 4
    chunk = bytearray()

    # exact audio rate over time (no integer-trunc drift)
    base_steps = audio_hz // cfg.fps_target
    rem_steps  = audio_hz %  cfg.fps_target
    step_acc   = 0

    # reuse fade surface (no per-frame alloc)
    fade = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)

    # palette by pc
    palette = [
        (0, 200, 180),   # teal
        (255, 140, 0),   # orange
        (180, 80, 255),  # violet
        (80, 160, 255),  # blue
        (255, 80, 140),  # pink
        (160, 255, 80),  # green
    ]

    def set_delay(new_delay: int) -> None:
        nonlocal delay_samples, delay_line
        new_delay = max(MIN_DELAY, min(MAX_DELAY, int(new_delay)))
        if new_delay == delay_samples:
            return
        delay_samples = new_delay
        if delay_samples <= 0:
            delay_line = deque([0], maxlen=1)
        else:
            delay_line = deque([0] * delay_samples, maxlen=delay_samples)

    def draw_pixel(row: int, col: int, sym: int) -> None:
        if sym != 1:
            return
        rect = pygame.Rect(col * scale, row * scale, scale, scale)
        pygame.draw.rect(canvas, (*TEAL, draw_alpha), rect)


    state = MachineState(tape=[0] * N)
    reset_machine(state, N)
    canvas.fill((0, 0, 0, 0))
    
    decay_surface = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)

    started_audio = False
    PRIME_CHUNKS = 3
    prime_count = 0

    running = True
    while running:
        # --- input ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                k = event.key
                if k in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif k == pygame.K_r:
                    reset_machine(state, N)
                    canvas.fill((0, 0, 0, 0))
                # delay knob: coarse and fine
                elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    set_delay(delay_samples - 64)   # coarse
                elif k in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    set_delay(delay_samples + 64)
                elif k == pygame.K_LEFTBRACKET:
                    set_delay(delay_samples - 1)    # fine
                elif k == pygame.K_RIGHTBRACKET:
                    set_delay(delay_samples + 1)
                elif k == pygame.K_COMMA:
                    decay_alpha = max(0, decay_alpha - 1)
                elif k == pygame.K_PERIOD:
                    decay_alpha = min(50, decay_alpha + 1)
                elif k == pygame.K_SEMICOLON:
                    draw_alpha = max(0, draw_alpha - 1)
                elif k == pygame.K_QUOTE:
                    draw_alpha = min(255, draw_alpha + 1)

        # --- determine steps this frame (exact audio_hz over time) ---
        steps = base_steps
        step_acc += rem_steps
        if step_acc >= cfg.fps_target:
            steps += 1
            step_acc -= cfg.fps_target

        # --- step machine + generate audio ---
        for _ in range(max(1, steps)):
            tc = state.i
            read_sym = state.tape[tc]
            rule = program[(state.pc, read_sym)]
            write_sym = rule.write

            # audio: Left = R(now), Right = delayed W
            L = bit_to_i16(read_sym == 1)
            w_now = bit_to_i16(write_sym == 1)
            if delay_samples <= 0:
                R = w_now
            else:
                delay_line.append(w_now)
                R = delay_line.popleft()

            chunk += struct.pack("<hh", L, R)

            # write + draw
            state.tape[tc] = write_sym
            row = (state.cycle // N) % N
            col = tc
            draw_pixel(row, col, write_sym) 
            
            # move + next
            state.i = (tc + rule.move) % N
            state.pc = rule.next_pc
            state.cycle += 1

            # queue audio chunk
            # queue audio chunk (prime a few buffers before "going live")
            if len(chunk) >= CHUNK_BYTES:
                snd = pygame.mixer.Sound(buffer=bytes(chunk))
                chunk.clear()

                if not started_audio:
                    # Fill the pipeline with a few chunks before we commit to real-time playback
                    if prime_count == 0:
                        chan.play(snd)
                    else:
                        chan.queue(snd)
                    prime_count += 1
                    if prime_count >= PRIME_CHUNKS:
                        started_audio = True
                else:
                    if chan.get_busy():
                        chan.queue(snd)
                    else:
                        # If we ever get here, we starved. Restart cleanly.
                        chan.play(snd)


        # --- caption (once per frame) ---
        delay_ms = 1000.0 * delay_samples / audio_hz if audio_hz else 0.0
        pygame.display.set_caption(
            f"FTMp parity N={N}  {audio_hz}Hz  delay={delay_samples} ({delay_ms:.1f}ms) brightness={draw_alpha} fade={decay_alpha}"
        )

        # --- decay / fade (once per frame) ---    
        if decay_alpha > 0:
            decay_surface.fill((*BG_COLOR, decay_alpha))
            canvas.blit(decay_surface, (0, 0))
                    
        # --- display ---
        screen.fill(BG_COLOR)
        screen.blit(canvas, (0, 0))
        pygame.display.flip()
        clock.tick(cfg.fps_target)

    pygame.quit()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=1024)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--audio_hz", type=int, default=22000)
    ap.add_argument("--program", type=str, default="program.csv")
    args = ap.parse_args()
    run_ftmp_forever(N=args.N, fps=args.fps, audio_hz=args.audio_hz, program_path=args.program)
