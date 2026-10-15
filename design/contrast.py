"""WCAG 2.x contrast for the aloud design tokens.

Run: python3 design/contrast.py
Every ratio quoted in design/DESIGN.md and design/directions.html comes from here.
"""

def luminance(hex_colour):
    h = hex_colour.lstrip('#')
    def channel(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(h[i:i + 2]) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


DIRECTIONS = {
    'Signal dark': dict(ground='#0B0B0A', raised='#171716', ink='#F4F3EE', inkSoft='#C8C7C0',
                        inkMuted='#A3A29B', voice='#FFD23F', onVoice='#0B0B0A',
                        dialogue='#63635F', alert='#FF8A7A'),
    'Signal light': dict(ground='#F7F6F1', raised='#FFFFFF', ink='#111110', inkSoft='#3B3B38',
                         inkMuted='#5C5B56', voice='#FFD23F', onVoice='#111110',
                         voiceInk='#6B5200', dialogue='#86857E', alert='#B3261E'),
    'Liner dark': dict(ground='#0E0D0C', raised='#1A1917', ink='#EFEAE0', inkSoft='#BDB6A9',
                       inkMuted='#9A9387', voice='#EFEAE0', onVoice='#0E0D0C',
                       dialogue='#66625A', alert='#F29B8B'),
    'Liner light': dict(ground='#F3EFE6', raised='#FBF9F4', ink='#191714', inkSoft='#45413A',
                        inkMuted='#635E55', voice='#191714', onVoice='#F3EFE6',
                        dialogue='#877F72', alert='#A3261A'),
    'Meter dark': dict(ground='#0F1213', raised='#1A1F21', ink='#EEF2F1', inkSoft='#B6C0BF',
                       inkMuted='#8E9A99', voice='#C8F23C', onVoice='#0F1213',
                       dialogue='#5A6664', alert='#FF8F80'),
    'Meter light': dict(ground='#F2F4F3', raised='#FFFFFF', ink='#101415', inkSoft='#3A4446',
                        inkMuted='#586466', voice='#C8F23C', onVoice='#101415',
                        voiceInk='#3F5A00', dialogue='#7F8987', alert='#B3261E'),
    'Current app': dict(ground='#0b0908', raised='#15100e', ink='#f7f1ea', inkSoft='#c2ae9d',
                        inkMuted='#a4907f', voice='#ff7a45', onVoice='#1b0d06',
                        dialogue='#4a3b33'),
}

if __name__ == '__main__':
    for name, t in DIRECTIONS.items():
        print(name)
        for k in ('ink', 'inkSoft', 'inkMuted', 'voice', 'voiceInk', 'alert'):
            if k in t:
                print(f"  {k:9} {t[k]}  {ratio(t[k], t['ground']):5.1f} on ground"
                      f"  {ratio(t[k], t['raised']):5.1f} on raised")
        print(f"  onVoice on voice        {ratio(t['onVoice'], t['voice']):5.1f}")
        print(f"  dialogue vs silence     {ratio(t['dialogue'], t['ground']):5.2f}  (graphic, needs 3.0)")
        print(f"  voice vs dialogue       {ratio(t['voice'], t['dialogue']):5.2f}  (graphic, needs 3.0)")
