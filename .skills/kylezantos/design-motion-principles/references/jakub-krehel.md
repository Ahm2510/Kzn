# Jakub Krehel Perspective
*Focus: Refined "materializing" animations and optical alignment.*

### 1. The "Jakub Recipe" for Enter Animations
A standard enter animation should feel like it's "coming into focus."
- **Properties**: Opacity (0→1) + TranslateY (subtle) + Blur (4px→0px).
- **Why**: The blur creates a sense of depth and physical presence that opacity alone misses.

### 2. Optical Alignment
Don't trust the math; trust your eyes.
- **Play Buttons**: The triangle icon is mathematically centered but visually heavy on the left. Shift it right.
- **Icon Buttons**: If a button only has an icon, the padding often needs manual adjustment to *look* centered.

### 3. Subtle Exits
Exits should never compete with enters.
- If an item enters with `translateY: 20px`, let it exit with `translateY: -8px` and a faster fade.
- The user's focus is on what's *new*, so the old stuff should disappear gracefully and quickly.

### 4. Shadows over Borders
In light mode, use multi-layer box-shadows to define depth instead of solid 1px borders. Shadows feel more "organic" and handle background transitions better.
