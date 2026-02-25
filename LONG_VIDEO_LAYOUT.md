LONG VIDEO LAYOUT (uses short layout from video_service.generate_video)

This file describes the visual sections of the long-video output (horizontal 1920x1080) and points to the code locations to edit text/graphics.

Overview (high-level order, visual top→bottom, left→right):

1) Background
- Purpose: full-bleed background (image or looping video)
- Where to change: [video_service.py](video_service.py#L60-L100) — background loading and fallback to `assets/bg.mp4`.
- Placeholder to edit: `shorts_bg_path` variable or replace with desired video path.

2) Overlay (semi-transparent dark layer)
- Purpose: improve text contrast over background
- Where to change: [video_service.py](video_service.py#L110-L120)
- Placeholder: `overlay` ColorClip opacity and color.

3) Anchor / Left visual (anchor image)
- Purpose: Static anchor visual on the left (shorts-style)
- Where to change: [video_service.py](video_service.py#L130-L140) — `anchor` ImageClip usage and position/size.
- Replace `static/anchor.png` or adjust `.set_position()` / `.resize()`.

4) Logo / Top center
- Purpose: Channel logo shown near top
- Where to change: [video_service.py](video_service.py#L146-L152) — `logo` ImageClip definition.
- Replace `static/logo.jpg` or change `height`/`position`.

5) Top headline bar / Ticker container
- Purpose: red headline bar and scrolling ticker text
- Where to change: [video_service.py](video_service.py#L158-L210) — `headline_bar`, `ticker_img_path`, `ticker_clip`, and ticker `make_ticker_position`.
- Text placeholders: `title` passed to `generate_video(title, description, ...)`.

6) Description / Right-side boxed text
- Purpose: Long descriptive text box shown on the right
- Where to change: [video_service.py](video_service.py#L220-L330) — `create_boxed_text_image`, `desc_img_path`, and description scrolling behavior.
- Text placeholders: `description` argument to `generate_video()`.

7) Per-story media area (if needed)
- Purpose: boxed area showing story images/videos (in short layout this is part of anchor/desc composition)
- Where to change: [video_service.py](video_service.py#L90-L160) and around the anchor/desc regions; for explicit per-story behaviour the previous `long_video_service.py` had custom logic but we now reuse short layout.

8) Bottom info bar / Source line
- Purpose: small info bar with channel + headline
- Where to change: [video_service.py](video_service.py#L340-L370) — info box generation and `create_ticker_text_image` usage.
- Placeholder text: constructed from `title`/`description` inside `generate_video`.

9) Side scrolling or additional ticker overlays
- Purpose: extra scrolling text on the right or side panels
- Where to change: [video_service.py](video_service.py#L380-L460) — side scrolling text creation (`create_ticker_text_image`, vertical scroll logic).

10) Ending screen
- Purpose: short "Thank you" end card
- Where to change: [video_service.py](video_service.py#L480-L520) — ending image/text composition.

Audio / Mixing
- Where to change: [video_service.py](video_service.py#L100-L120) and around `AudioFileClip` usage — background music path `assets/music.mp3` and volume `volumex(0.1)`.

How to edit text content for long video layout
- Primary text fields are `title` and `description` passed into `generate_video(title, description, audio_path, ...)`.
- If you want specific per-section text (e.g., lower-thirds labeled "Hook", "What Happened"), point me to the exact words and I will add an explicit mapping and controlled insertion points.

Suggested next steps for you
- Reply with exact text replacements per section (e.g., "Top headline: Replace with 'Today: Floods in X'", "Bottom info bar prefix: 'Grahak Chetna | '"), using these section names.
- If you'd like the older long-only features restored (per-story green-box, Pexels fallback, and looping ticker), specify which ones to re-enable; otherwise I'll keep the simplified short-layout wrapper.

Notes
- Current long video generation delegates to [video_service.py](video_service.py). To change layout details we edit that file; for per-story bespoke behavior we can reintroduce custom code into `long_video_service.py` and call helper functions in `video_service.py`.
