#  Copyright (c) 2021, Matthew Broadway
#  License: MIT License
import argparse

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

import ezdxf
from ezdxf.addons.drawing import Properties, RenderContext, Frontend
from ezdxf.addons.drawing.backend import prepare_string_for_rendering
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.properties import LayoutProperties
from ezdxf.math import Matrix44, X_AXIS
from ezdxf import zoom
from ezdxf.addons.drawing.config import Configuration, LinePolicy


class FixedSizedTextMatplotlibBackend(MatplotlibBackend):
    """Export text in PDF as characters and not as PathPatch() for a smaller
    file size.
    This backend does not support reflections (mirroring), text width factor and
    oblique angles (slanted text).
    Each DXF file has its own individual text scaling factor, depending on the
    extents of the drawing and the output resolution (DPI), which must be
    determined by testing.
    The TrueType fonts are not embedded and may be replaced by other fonts in
    the PDF viewer.
    For more information see github discussion #582:
    https://github.com/mozman/ezdxf/discussions/582
    """
    def __init__(
        self,
        ax: plt.Axes,
        text_size_scale: float = 2,
        *,
        adjust_figure: bool = True,
        font: FontProperties = FontProperties(),
    ):
        self._text_size_scale = text_size_scale
        super().__init__(
            ax, adjust_figure=adjust_figure, font=font, use_text_cache=False
        )

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
        x, y, _, _ = transform.get_row(3)
        rotation = transform.transform_direction(X_AXIS).angle_deg
        self.ax.text(
            x,
            y,
            text.replace("$", "\\$"),
            #color=properties.color,
            color='k',
            size=cap_height * self._text_size_scale,
            rotation=rotation,
            in_layout=True,
            fontproperties=font_properties,
            transform_rotates_text=True,
            zorder=self._get_z(),
        )


def main():
    #parser = argparse.ArgumentParser()
    #parser.add_argument('dxf_file')
    #parser.add_argument('output_path')
    #parser.add_argument(
    #    "--scale",
    #    "-s",
    #    type=float,
    #    default=1.0,
    #    help="text scaling factor",

    #)
    #args = parser.parse_args()

    doc = ezdxf.readfile("a0100.dxf")

    #layout = doc.modelspace()
    #zoom.extents(layout)
    layout = doc.layout('Layout0')
    zoom.extents(layout)
    print(layout.dxf.extmin)
    print(layout.dxf.extmax)
    print(layout.dxf.limmin)
    print(layout.dxf.limmax)
    print(layout)
    key = doc.layouts.get_active_layout_key()
    paperspace=doc.layouts.get_layout_by_key(key)
    print(paperspace.get_paper_limits())
    #paperspace.page_setup(size=(297, 210), margins=(0, 0, 0, 0), units='mm', offset=(0, 0), rotation=0, scale=16, name='ezdxf', device='printdevice.pc3')
    print(paperspace.get_paper_limits())
    #zoom.extents(paperspace)
    print(paperspace.get_paper_limits())
    print(paperspace)
    #layout = layout.page_setup(size=(297, 210), margins=(0, 0, 0, 0), units='mm', offset=(0, 0), rotation=0, scale=16,
                              # name='ezdxf', device='printdevice.pc3')
    #layout.reset_limits()
    #layout.set_plot_type(2)
    #layout.set_plot_style("monochrome.ctb")
    #layout.zoom_to_paper_on_update(True)
    #layout.update_paper(True)
    #doc.p
    #layout = layout.page_setup(size=(297, 210), margins=(0, 0, 0, 0), units='mm', offset=(0, 0), rotation=0, scale=16, name='ezdxf',device='printdevice.pc3')


    fig: plt.Figure = plt.figure()
    ax: plt.Axes = fig.add_axes((0, 0, 1, 1))

    config = Configuration.defaults()
    config = config.with_changes(
        line_policy=LinePolicy.ACCURATE
        #if args.ltype == "ezdxf"
        #else config.line_policy
    )

    ctx = RenderContext(layout.doc)
    layout_properties = LayoutProperties.from_layout(paperspace)
    out = FixedSizedTextMatplotlibBackend(ax, text_size_scale=1.2)
    Frontend(ctx, out, config=config).draw_layout(
        paperspace,
        finalize=True,
        layout_properties=layout_properties,
    )
    fig.savefig(
        'a0100_pdf2.pdf',
        dpi=300,
        facecolor=ax.get_facecolor(),
        #facecolor='w',
        edgecolor='k',
        transparent=True,
        #papertype='a4',
    )
    plt.close(fig)


if __name__ == "__main__":
    main()