import argparse
import math

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

import ezdxf
from ezdxf.addons.drawing import Properties, RenderContext, Frontend
from ezdxf.addons.drawing.backend import prepare_string_for_rendering
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.properties import LayoutProperties
from ezdxf.math import Matrix44


class FixedSizedTextMatplotlibBackend(MatplotlibBackend):
    def __init__(
            self,
            ax: plt.Axes,
            text_size_scale: float = 2,
            *,
            adjust_figure: bool = True,
            font: FontProperties = FontProperties(),
    ):
        self._text_size_scale = text_size_scale
        super().__init__(ax, adjust_figure=adjust_figure, font=font, use_text_cache=False)

    def draw_text(
            self,
            text: str,
            transform: Matrix44,
            properties: Properties,
            cap_height: float,
    ):
        if not text.strip():
            return  # no point rendering empty strings
        font_properties = self.get_font_properties(properties.font)
        assert self.current_entity is not None
        text = prepare_string_for_rendering(text, self.current_entity.dxftype())
        scale = self._text_renderer.get_scale(cap_height, font_properties)
        text_transform = Matrix44.scale(scale) @ transform
        x, y, _, _ = text_transform.get_row(3)
        scale = math.sqrt(sum(i * i for i in text_transform.get_row(0)))
        self.ax.text(
            x, y, text.replace('$', '\\$'),
            color=properties.color, size=3, in_layout=True,
            fontproperties=font_properties, transform_rotates_text=False, zorder=self._get_z()
        )
        #self.ax.text(
        #    x, y, text.replace('$', '\\$'),
        #    color=properties.color, size=1 * scale * self._text_size_scale, in_layout=True,
        #    fontproperties=font_properties, transform_rotates_text=True, zorder=self._get_z()
        #)

def main():
    #parser = argparse.ArgumentParser()
    #parser.add_argument('dxf_file')
    #parser.add_argument('output_path')
    #args = parser.parse_args()

    #doc = ezdxf.readfile(args.dxf_file)
    doc = ezdxf.readfile('a0100.dxf')
    layout = doc.modelspace()

    fig: plt.Figure = plt.figure()
    ax: plt.Axes = fig.add_axes((0, 0, 1, 1))
    ctx = RenderContext(layout.doc)
    layout_properties = LayoutProperties.from_layout(layout)
    out = FixedSizedTextMatplotlibBackend(ax)
    # out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(
        layout,
        finalize=True,
        layout_properties=layout_properties,
    )
    fig.savefig(
        'a0100_pdf.pdf', dpi=300, facecolor=ax.get_facecolor(), transparent=True
    )
    plt.close(fig)


if __name__ == '__main__':
    main()