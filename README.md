# finite-turing-machine-parity-fugue
This is a finite Turing machine whose state can be listened to.
FTM — Finite Turing Machine (Parity Fugue)
This repository contains a small finite Turing machine that you can watch and listen to while it runs.
It is not a music program.
It is not a visualization demo.
It is a machine.
________________________________________
What it is
•	A finite tape Turing machine (FTM)
•	A minimal read / write / move / next-state rule table
•	One machine cycle → one audio sample
•	Two audio channels:
o	Left = R (read register)
o	Right = W (write register)
•	Optional delay between R and W creates audible structure
The machine executes deterministically.
No randomness. No AI. No score.
________________________________________
What you’ll notice
•	The machine produces audible structure on its own.
•	Long runs of stability create low-frequency “pedal tones.”
•	Recurrence creates stereo motion and spatial effects.
•	Small changes (tape length, delay, decay) matter a lot.
If you’ve ever listened to logic probes, delay lines, or feedback systems, this will feel familiar.
________________________________________
How to run
Requirements:
•	Python 3.10+
•	pygame
pip install pygame
python FTM.py --N 1024 --audio_hz 22000
Adjust parameters from the keyboard while it runs.
________________________________________
Controls (typical)
•	+ / -  Adjust R↔W delay (coarse)
•	[ / ]  Adjust delay (fine)
•	, / .  Decay rate (visual persistence)
•	; / '  Ink brightness
•	r   Reset machine
•	q / ESC Quit
(Exact mappings are in the source.)
________________________________________
Files
•	program.csv
The state table. This is the machine.
•	FTM*.py
The runtime: tape, clock, audio, and rendering.
Nothing is hidden.
________________________________________
What this is for
This is for people who like:
•	minimal machines
•	feedback and delay
•	deterministic systems with emergent behavior
•	understanding something by letting it run
If you want a “result,” record it.
If you want a picture, render it.
If you want a different behavior, change the rule table.
________________________________________
What it is not
•	Not optimized
•	Not polished
•	Not interactive in a musical sense
•	Not intended to be “performed”
It’s closer to a bench instrument than a composition.
________________________________________
Provenance
This machine descends from hand-built FTMs and logic experiments dating back decades.
It is presented here as-is, without claims.
Trade it like a recipe.

