from IPython.display import SVG, display
from boxes.generators.rack_box import DividerTray

fn = "rack_box.svg"
b = DividerTray(
    sx=[108],
    sy=[40, 40, 35, 15],
    bottom=True,
    h=45,
    reference=0,
    debug=0,
    output=fn,
    labels=True,
)
fn = "rack_box.svg"
b.open()
b.render()
b.close()

display(SVG(fn))

# from IPython.display import SVG, display
# from boxes.generators.rack_box import DividerTray

# b = DividerTray(sx="108", sy=[40, 40, 35, 15], bottom_wall=True, h=45)
# fn = "rack_box.svg"
# b.parseArgs(["--reference=0", "--debug=0", "--output=" + fn])
# b.open()
# b.render()
# b.close()

# display(SVG(fn))
