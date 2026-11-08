# UI Design Rules for Agents

Status: draft for owner review
Sources: `typography for agents/typography.md` and seven "Do's and Don'ts" cheat sheets (UI, typography, layout/spacing, color, mobile, dashboard, dark mode) kept in the owner's typography folder.

Check every screen against these rules before showing it to the owner.

Rules marked **(default)** are starting points. Break them when the design needs it, and say so in the change summary when you do.

---

## 1. Typography

- **Line height:** body text at 1.4 to 1.6. Text set tighter is hard to follow from one line to the next.
- **Line length:** aim for 45 to 75 characters per line. Very long lines make the eye lose its place on the return sweep. Constrain the container width if needed.
- **Hierarchy:** headings must be clearly bigger or bolder than body text. Do not rely on a heading that looks like body text.
- **Capitals:** save all caps for short labels (e.g. a small eyebrow such as "TRIAL ENDING"). Never set sentences or paragraphs in all caps.
- **Typefaces:** use one or two typefaces. Create variety with weight and size, not with extra fonts. Do not mix serif, mono and sans in one short block.
- **Large headings:** tighten letter spacing on large headings so the letters do not look loose.
- **Text contrast:** body text needs at least 4.5:1 contrast against its background. Light grey placeholder-looking text used for real content fails this.

## 2. Spacing and layout

- **Spacing scale:** pick all gaps, padding and margins from one scale: **4, 8, 16, 24, 32**. (default) Do not use one-off values such as 7, 13, 22 or 29.
- **Labels:** keep a label closer to its own field than to the field above it.
- **Groups:** use more space between groups than within a group. Related items stay close; unrelated items get space.
- **Alignment:** align everything on one edge. Do not mix centred and left-aligned blocks in the same group. (default)
- **Card padding:** pad cards with **16px or more**. (default)
- **Nested corners:** inner radius = outer radius minus padding, never below 0. Example: outer 20 with 12 padding gives inner 8. Do not put a 20px radius inside a 20px radius.
- **Long text:** left-align anything longer than two lines. Do not centre paragraphs.

## 3. Color

- **One accent:** use one accent colour, and only for the main action on a view. Other buttons are neutral (outlined or grey). (default)
- **Errors:** never show an error with colour alone. Add a message in words (e.g. "Add the end, like .com"). A red border alone is not enough.
- **Fixed meanings:** red means danger or destructive; green means success. Do not reuse them for decoration or for unrelated actions. A "Keep" button should not be green when "Delete" is red.
- **Text on colour:** check contrast on coloured buttons and badges too. The minimum is **4.5:1**. Yellow with dark text can pass; yellow with white text usually does not.
- **Saturation:** use soft tints for large areas (backgrounds, panels). Use strong colour only for small details (icons, badges, the one action). A full-saturation panel behind text tires the eye.
- **Links:** links need colour **and** an underline.
- **Charts:** highlight one series in the accent colour and gray out the rest. Do not draw many equally strong lines.

## 4. Buttons, actions and copy

- **One primary action per view.** Secondary actions are neutral. Do not place two filled primary buttons side by side.
- **Button copy says what happens.** Use "Delete this project?" with "Keep" / "Delete", not "Are you sure?" with "No" / "OK".
- **Hover is not a control.** Actions must not appear only on hover. Show them on screen (for example a visible "..." menu).

## 5. Forms

- **Labels stay visible.** Placeholders disappear as soon as the user types, so the label must stay above the field. Do not use a placeholder as the only label.
- **Placeholder text** is an example, not a label (e.g. "you@mail.com").
- **Input type:** set the right input type (email, tel, number, url) so the correct keyboard opens.

## 6. Mobile

- **Tap targets:** at least **44 x 44** points. Smaller targets are easy to miss.
- **Main action at the bottom**, where the thumb rests. (default)
- **Input text:** at least **16px**. Smaller text makes iPhone zoom in on focus.
- **Dialogs:** use bottom sheets instead of small centred dialogs. (default)
- **No hover-only actions.** A phone has no hover.

## 7. Dashboards and data

- **Lead with the one number that matters most.** Put it first and largest. (default)
- **Every number gets a period and a change.** Example: "$62,940, Revenue, October, +8.1% vs September". A bare number with no context is not useful.
- **Bar charts start at zero.** A bar axis that starts at 90 makes 92 look three times larger than 91. Truncated axes are not allowed on bar charts.
- **Parts of a whole:** if there are more than 3 parts, use sorted horizontal bars, not a pie chart. (default)
- **Tables:** right-align numbers so the digits line up. Left-align text columns.
- **Highlight one line, gray out the rest.** (default)

## 8. Dark mode

- **Background:** use dark grey, not pure black. Pure black with white text causes glare.
- **Text:** use off-white, not pure white. Create hierarchy with tone (lighter for primary, dimmer grey for secondary), not only with size.
- **Brand colours:** use lighter, less saturated tints of the accent on dark backgrounds. A saturated blue that works on white can vibrate on black.
- **Elevation:** shadows disappear on dark backgrounds. Raise surfaces with slightly lighter greys instead.
- **Contrast:** grey secondary text still needs **4.5:1**. Dim grey on dark grey often fails.
- **Images:** bright images need a dark variant, or should be dimmed, so they do not glare.

## 9. Pre-ship checklist

Before showing a screen to the owner, confirm each item:

- [ ] Body line height 1.4 to 1.6; line length 45 to 75 characters.
- [ ] Headings clearly bigger or bolder than body; no all-caps paragraphs.
- [ ] One or two typefaces only.
- [ ] Gaps and padding come from 4, 8, 16, 24, 32; cards padded 16px or more.
- [ ] Groups separated by more space than items within them; labels closer to their fields.
- [ ] Nested radii computed as outer minus padding.
- [ ] One accent colour, used only for the main action.
- [ ] Errors have words, not just colour; red and green keep fixed meanings.
- [ ] Text on coloured surfaces and grey text meet 4.5:1 contrast.
- [ ] Links are coloured and underlined.
- [ ] Mobile: tap targets 44 x 44; inputs 16px; main action at the bottom; no hover-only actions.
- [ ] Dashboard: headline number first; each number has a period and a change; bar charts start at zero; numbers right-aligned.
- [ ] Dark mode: dark grey background; off-white text; no shadows used for elevation.

## Related

- Repo workflow and verification rules: [`DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md)
- Design work under the repo: [`design/`](design/)
