# Volt Trace

Full-colour Python 3 neon **light-cycle** arcade for [ElbowOS](https://x.com/ElbowOS).

Steer a cyan ribbon. Survive the amber AI. Crash ribbons spark, then peel back so the duel keeps moving.

## Play

```bash
pip install -r requirements.txt
python3 volt_trace.py --play
```

Arrow keys turn 90°. `R` resets. `Esc` quits.

## Autoplay reel (headless 9:16)

```bash
SDL_VIDEODRIVER=dummy python3 volt_trace.py
```

Writes a 15s 1080×1920 H.264 MP4 (title + score + `x.com/ElbowOS` burned in).

## Links

- Featured account: https://x.com/ElbowOS
- Reel on Drive: https://drive.google.com/file/d/1-vOw0Yr5yOdAEmPKiIrN5LnSU9vluN_A/view?usp=drivesdk

MIT.
