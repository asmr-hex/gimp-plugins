#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gimpfu import *
from array import array
import math


# overlap (DEBUG: we need Python array elementwise addition....because we are currently overwriting data.)
# padding!
# rotation oscillation!

EFFICIENT=True

def add_src_rgn(src_rgn, dest_rgn):
    if EFFICIENT:
        dest_rgn[:,:] = array("B", src_rgn[:,:]).tostring()
    else:
        for i in range(dest_rgn.w):
            for j in range(dest_rgn.h):
                # print(str(i) + " " + str(j))
                src_pixel = bytearray(src_rgn[i + src_rgn.x, j + src_rgn.y])
                # updated_dest_pixel = bytearray(dest_rgn[i + dest_rgn.x, j + dest_rgn.y])
                if src_pixel[0] + src_pixel[1] + src_pixel[2] < 5:
                    continue
                
                dest_rgn[i + dest_rgn.x, j + dest_rgn.y] = str(src_pixel)

def tile_selection_plugin(image, layer, tileRows, tileColumns, overlapX, overlapY, osc_amplitude, osc_period, offsetY, offsetX):
    # create new layer that is the same size of the current layer
    new_layer = pdb.gimp_layer_new(
        image,
        layer.width,
        layer.height,
        layer.type,
        layer.name + "-tiled",
        100.00,
        NORMAL_MODE,
    )

    # group undo to a single operation.
    pdb.gimp_image_undo_group_start(image)
    pdb.gimp_progress_init("generating tiles.", None)

    # get the pixel region from the selection in the active layer
    is_selection, x1, y1, x2, y2 = pdb.gimp_selection_bounds(image)
    layer_selection_x = x1 - layer.offsets[0]
    layer_selection_y = y1 - layer.offsets[1]
    selection_width = x2 - x1
    selection_height = y2 - y1
    # src_pixel_rgn = layer.get_pixel_rgn(
    #     layer_selection_x,
    #     layer_selection_y,
    #     selection_width,
    #     selection_height,
    #     False,
    #     False
    # ) # read only.
    # src_pixels = array("B", src_pixel_rgn[:,:]) # create an array of unsigned chars

    if selection_width > layer.width or selection_height > layer.height:
        pdb.gimp_message("The selection must be smaller than the size of the current layer.")
        pdb.gimp_image_undo_group_end(image)
        return
    
    # create new selection for new layer
    pdb.gimp_image_select_rectangle(image, CHANNEL_OP_ADD, 0, 0, layer.width, layer.height)

    ampl = (osc_amplitude/100.0)*selection_height
    
    # create copies of the selection on original layer
    for column in range(tileColumns):
        for row in range(tileRows):
            f = (math.pi*2)*((column*selection_width)/((osc_period/100.0)*layer.width))
            dest_rgn_y = int(row*selection_height + ampl*math.sin(f) - ((overlapY/100.0) * (row + 1) * selection_height) + (offsetY * selection_height))
            dest_rgn_x = int(column*selection_width - ((overlapX/100.0) * (column + 1) * selection_width) + (offsetX * selection_width))
            dest_pixel_rgn = new_layer.get_pixel_rgn(
                dest_rgn_x,
                dest_rgn_y,
                selection_width,
                selection_height,
                True,  # dirty region (mutable)
                True,  # draw in shadow buffer
            )

            # skip if the destination region is completely out of bounds
            if dest_pixel_rgn.w <= 1 or dest_pixel_rgn.h <= 1:
                continue
                
            # if destination pixel region is smaller than src pixel region

            # account for tiles occluded at the top
            negative_offset_y = 0
            if dest_rgn_y <= 1:
                negative_offset_y = -dest_rgn_y

            # account for tiles occluded at left
            negative_offset_x = 0
            if dest_rgn_x <= 1:
                negative_offset_x = -dest_rgn_x

            add_src_rgn(
                layer.get_pixel_rgn(
                    layer_selection_x + negative_offset_x,
                    layer_selection_y + negative_offset_y,
                    dest_pixel_rgn.w,
                    dest_pixel_rgn.h,
                    False,
                    False
                ),
                dest_pixel_rgn,
            )
            # dest_pixel_rgn[:,:] = array(
            #     "B",
            #     layer.get_pixel_rgn(
            #         layer_selection_x + negative_offset_x,
            #         layer_selection_y + negative_offset_y,
            #         dest_pixel_rgn.w,
            #         dest_pixel_rgn.h,
            #         False,
            #         False
            #     )[:,:]
            # ).tostring()

        pdb.gimp_progress_update(column/float(tileColumns))

    # add layer to image
    image.add_layer(new_layer)

    new_layer.merge_shadow()
    new_layer.update(0, 0, new_layer.width, new_layer.height)
    new_layer.flush()
    gimp.displays_flush()
    pdb.gimp_image_undo_group_end(image)

    return

register(
    "tile_selection_plugin", # proc_name
    "tiles contents of a selection", # blurb
    "takes a layer and creates a new layer that is the tiled contents of the input layer",  # help
    "coco", # author
    "GPL3", # copyright
    "2021", # date
    "Selection Tiler", # label
    "*", # imagetypes
    [  
        (PF_IMAGE, "image", "Input image", None),
        (PF_DRAWABLE, "drawable", "Input drawable", None),
        (PF_INT, "tile_rows", "Tile rows", 8),
        (PF_INT, "tile_columns", "Tile columns", 8),
        (PF_SLIDER, "tile_overlap_x", "Tile X Overlap (% of tile width)", 0, (0, 100, 1)),
        (PF_SLIDER, "tile_overlap_y", "Tile Y Overlap (% of tile height)", 0, (0, 100, 1)),
        (PF_SLIDER, "tile_osc_ampplitude", "Tile oscillation amplitude (% of tile height)", 0, (0, 100, 1)),
        (PF_SLIDER, "tile_osc_period", "Tile oscillation period (% of tile pattern width)", 100, (1, 100, 1)),
        (PF_INT, "tile_top_offset", "Tile Top Offset", 0),
        (PF_INT, "tile_left_offset", "Tile Left Offset", 0),
    ],  # params
    [
        #(PF_LAYER, "new_layer", "Output layer", None)
    ],  # results
    tile_selection_plugin, # function
    menu="<Image>/Filters/Map/" # menu
)

main()
