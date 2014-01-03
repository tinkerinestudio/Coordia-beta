#!/usr/bin/env python

YAGV_VERSION = "0.3b"

import pyglet

# Disable error checking for increased performance
pyglet.options['debug_gl'] = False

from pyglet import clock
from pyglet.gl import *
from pyglet.window import key
from pyglet.window import mouse

from gcodeParser import *
import os.path
import time

class App:
        def __init__(self):
                
                self.RX = 0.0
                self.RZ = 0.0
                self.zoom = 1.0
        def run(self, path, machineNum):
                print
                print "Parsing '%s'..."%path
                print
                self.machineNum = machineNum
                self.parser = GcodeParser(self.machineNum)
                
                self.model = self.parser.parseFile(path)
                
                #self.parser.parse_G1(self.parser,'X209.247 Y90.834 Z0.1 F1080.0 E0.0307')

                #print
                #print "Done! %s"%self.model
                #print
                
                # default to the middle layer
                #self.layerIdx = len(self.model.layers)/2
                self.layerIdx = len(self.model.layers)-1
                
                return self
                
        def renderVertices(self):
                t1 = time.time()
                
                self.vertices = []
                #for x in range(-5, 5):
                #    glVertex2i(-5,x); glVertex2i(5,x)
                #for x in range(-5, 5):
                #    glVertex2i(x,-5); glVertex2i(x,5)
                for layer in self.model.layers:
                        
                        layer_vertices = []
                        
                        x = layer.start["X"]
                        y = layer.start["Y"]
                        z = layer.start["Z"]
                        for seg in layer.segments:
                                layer_vertices.append(x)
                                layer_vertices.append(y)
                                layer_vertices.append(z)
                                x = seg.coords["X"]
                                y = seg.coords["Y"]
                                z = seg.coords["Z"]
                                layer_vertices.append(x)
                                layer_vertices.append(y)
                                layer_vertices.append(z)
                                
                        self.vertices.append(layer_vertices)
                        
                t2 = time.time()
                #print "end renderColors in %0.3f ms" % ((t2-t1)*1000.0, )
        
        def renderIndexedColors(self):
                t1 = time.time()
                # pre-render segments to colors in the index
                styleToColoridx = {
                        "extrude" : 0,
                        "fly" : 1,
                        "retract" : 2,
                        "restore" : 3
                        }
                
                # all the styles for all layers
                self.vertex_indexed_colors = []
                
                # for all layers
                for layer in self.model.layers:
                        
                        # index for this layer
                        layer_vertex_indexed_colors = []
                        for seg in layer.segments:
                                # get color index for this segment
                                styleCol = styleToColoridx[seg.style]
                                # append color twice (once per end)
                                layer_vertex_indexed_colors.extend((styleCol, styleCol))
                        
                        # append layer to all layers
                        self.vertex_indexed_colors.append(layer_vertex_indexed_colors)
                t2 = time.time()
                #print "end renderIndexedColors in %0.3f ms" % ((t2-t1)*1000.0, )
        
        def renderColors(self):
                t1 = time.time()
                
                self.vertex_colors = [[],[],[]]
                
                # render color index to real colors
                colorMap = [
                                # 0: old layer
                                [[255,255,255, 50],[255,  0,  0, 0],[  0,  255,  0, 0],[  255,  255,  255, 60]], # extrude, fly, retract, restore
                                # 1: current layer
                                [[255,255,255,255],[255,  0,  0, 0],[  0,  255,  0,0],[  255,  255,  255, 100]], # extrude, fly, retract, restore
                                # 2: limbo layer
                                [[255,255,255, 10],[255,  0,  0, 0],[  0,  255,  0, 0],[  255,  255,  255, 100]] # extrude, fly, retract, restore
                                ]
                
                # for all 3 types
                for display_type in xrange(3):
                        
                        type_color_map = colorMap[display_type]
                        
                        # for all preindexed layer colors
                        for indexes in self.vertex_indexed_colors:
                                
                                # render color indexes to colors
                                colors = map(lambda e: type_color_map[e], indexes)
                                # flatten color values
                                fcolors = []
                                map(fcolors.extend, colors)
                                
                                # push colors to vertex list
                                self.vertex_colors[display_type].append(fcolors)
                                
                t2 = time.time()
                #print "end renderColors in %0.3f ms" % ((t2-t1)*1000.0, )
        
        def generateGraphics(self):
                t1 = time.time()
                
                self.graphics_old = []
                self.graphics_current = []
                self.graphics_limbo = []
                
                for layer_idx in xrange(len(self.vertices)):
                        nb_layer_vertices = len(self.vertices[layer_idx])/3
                        vertex_list = pyglet.graphics.vertex_list(nb_layer_vertices,
                                ('v3f/static', self.vertices[layer_idx]),
                                ('c4B/static', self.vertex_colors[0][layer_idx])
                        )
                        self.graphics_old.append(vertex_list)
                        
                        vertex_list = pyglet.graphics.vertex_list(nb_layer_vertices,
                                ('v3f/static', self.vertices[layer_idx]),
                                ('c4B/static', self.vertex_colors[1][layer_idx])
                        )
                        self.graphics_current.append(vertex_list)
                        
                        vertex_list = pyglet.graphics.vertex_list(nb_layer_vertices,
                                ('v3f/static', self.vertices[layer_idx]),
                                ('c4B/static', self.vertex_colors[2][layer_idx])
                        )
                        self.graphics_limbo.append(vertex_list)
                #       print nb_layer_vertices, len(self.vertices[layer_idx]), len(self.colors[0][layer_idx])
                
                t2 = time.time()
                #print "end generateGraphics in %0.3f ms" % ((t2-t1)*1000.0, )
                
class MyWindow(pyglet.window.Window):
        
        # events
        def on_resize(self, width, height):
                glViewport(0, 0, width, height)
                self.placeLabels(width, height)
                #app.render(width, height)
                
                return pyglet.event.EVENT_HANDLED

        def on_mouse_press(self, x, y, button, modifiers):
                #print "on_mouse_press(x=%d, y=%d, button=%s, modifiers=%s)"%(x, y, button, modifiers)
                if button & mouse.LEFT:
                        rotate_drag_start(x, y, button, modifiers)
                        
                if button & mouse.RIGHT:
                        layer_drag_start(x, y, button, modifiers)


        def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
                #print "on_mouse_drag(x=%d, y=%d, dx=%d, dy=%d, buttons=%s, modifiers=%s)"%(x, y, dx, dy, buttons, modifiers)
                if buttons & mouse.LEFT:
                        rotate_drag_do(x, y, dx, dy, buttons, modifiers)
                        
                if buttons & mouse.RIGHT:
                        layer_drag_do(x, y, dx, dy, buttons, modifiers)


        def on_mouse_release(self, x, y, button, modifiers):
                #print "on_mouse_release(x=%d, y=%d, button=%s, modifiers=%s)"%(x, y, button, modifiers)
                if button & mouse.LEFT:
                        rotate_drag_end(x, y, button, modifiers)
                        
                if button & mouse.RIGHT:
                        layer_drag_end(x, y, button, modifiers)

            
        def placeLabels(self, width, height):
                x = 5
                y = 5
                for label in blLabels:
                        label.x = x
                        label.y = y
                        y += 20
                        
                x = width - 5
                y = 5
                for label in brLabels:
                        label.x = x
                        label.y = y
                        y += 20
                        
                x = 5
                y = height - 5
                for label in tlLabels:
                        label.x = x
                        label.y = y
                        y -= 20
                        
                x = width - 5
                y = height - 5
                for label in trLabels:
                        label.x = x
                        label.y = y
                        y -= 20


        def on_mouse_scroll(self, x, y, dx, dy):
                # zoom on mouse scroll
                delta = dx + dy
                z = 1.1 if delta>0 else 1/1.1
                #print z
                app.zoom = min(15,max(0.4, app.zoom * z))
                

            
        def on_draw(self):
                #print "draw"
                
                # Clear buffers
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                
                # setup projection
                glMatrixMode(GL_PROJECTION)
                glLoadIdentity()
                gluPerspective(65, window.width / float(window.height), 0.1, 1000)
                
                # setup camera
                glMatrixMode(GL_MODELVIEW)
                glLoadIdentity()
                gluLookAt(0,1.5,2,0,0,0,0,1,0)
                
                # enable alpha blending
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                
                # rotate axes to match reprap style
                glRotated(-90, 1,0,0)
                # user rotate model
                glRotated(-app.RX, 1,0,0)
                glRotated(app.RZ, 0,0,1)
                
                glTranslated(0.1,0.0,-0.6)
                
                # draw axes
                glBegin(GL_LINES)
                glColor3f(1,0,0)
                glVertex2i(0,0); glVertex2i(0,1)
                glColor3f(0,1,0)
                glVertex2i(0,0); glVertex2i(0,1)
                glColor3f(0,0,1)
                glVertex2i(0,0); glVertex3i(0,0,1)
                
                #glColor3f(1,1,1)
                #glVertex2i(0,0); glVertex2i(5,0)
                # fit & user zoom model
                
                #draw a grid. not a good one though. 
                #glColor3f(1,1,1)
                #for x in range(-5, 6):
                #    glVertex2i(-5,x); glVertex2i(5,x)
                #for x in range(-5, 6):
                #    glVertex2i(x,-5); glVertex2i(x,5)
                    
                glEnd()
                
                # fit & user zoom model
                scale = app.zoom / max(app.model.extents[0], app.model.extents[2], app.model.extents[5])
                #glScaled(scale, scale, scale)
                glScalef(scale, scale, scale)
                
                glLineWidth(1)
                # Draw the model layers
                # lower layers
                for graphic in app.graphics_old[0:app.layerIdx]:
                        graphic.draw(GL_LINES)
                
                glLineWidth(2)
                
                # highlighted layer
                graphic = app.graphics_current[app.layerIdx]
                graphic.draw(GL_LINES)
                
                glLineWidth(1)
                # limbo layers
                for graphic in app.graphics_limbo[app.layerIdx+1:]:
                        graphic.draw(GL_LINES)
                
                
                # disable depth for HUD
                glDisable(GL_DEPTH_TEST)
                glDepthMask(0)
                
                #Set your camera up for 2d, draw 2d scene
                
                glMatrixMode(GL_PROJECTION)
                glLoadIdentity();
                glOrtho(0, window.width, 0, window.height, -1, 1)
                glMatrixMode(GL_MODELVIEW)
                glLoadIdentity()
                
                fpsLabel.text = "%d fps"%int(round(pyglet.clock.get_fps()))
                
                for label in blLabels:
                        label.draw()
                for label in brLabels:
                        label.draw()
                for label in tlLabels:
                        label.draw()
                for label in trLabels:
                        label.draw()
                
                # reenable depth for next model display
                glEnable(GL_DEPTH_TEST)
                glDepthMask(1)
                #print(ord(getch()))

def rotate_drag_start(x, y, button, modifiers):
        app.rotateDragStartRX = app.RX
        app.rotateDragStartRZ = app.RZ
        app.rotateDragStartX = x
        app.rotateDragStartY = y
        

def rotate_drag_do(x, y, dx, dy, buttons, modifiers):
        # deltas
        deltaX = x - app.rotateDragStartX
        deltaY = y - app.rotateDragStartY
        # rotate!
        app.RZ = app.rotateDragStartRZ + deltaX/5.0 # mouse X bound to model Z
        app.RX = app.rotateDragStartRX + deltaY/5.0 # mouse Y bound to model X
        #print app.asdf

def rotate_drag_end(x, y, button, modifiers):
        app.rotateDragStartRX = None
        app.rotateDragStartRZ = None
        app.rotateDragStartX = None
        app.rotateDragStartY = None


def layer_drag_start(x, y, button, modifiers):
        app.layerDragStartLayer = app.layerIdx
        app.layerDragStartX = x
        app.layerDragStartY = y


def layer_drag_do(x, y, dx, dy, buttons, modifiers):
        # sum x & y
        delta = x - app.layerDragStartX + y - app.layerDragStartY
        # new theoretical layer
        app.layerIdx = int(app.layerDragStartLayer + delta/5)
        # clamp layer to 0-max
        app.layerIdx = max(min(app.layerIdx, app.model.topLayer), 2)
        
        layerLabel.text = "layer %d"%(app.layerIdx-1)
        #global asdf
        #asdf = delta/50.0
#       # clamp layer to 0-max, with origin slip
#       if (app.layerIdx < 0):
#               app.layerIdx = 0
#               app.layerDragStartLayer = 0
#               app.layerDragStartX = x
#               app.layerDragStartY = y
#       if (app.layerIdx > len(app.model.layers)-1):
#               app.layerIdx = len(app.model.layers)-1
#               app.layerDragStartLayer = len(app.model.layers)-1
#               app.layerDragStartX = x
#               app.layerDragStartY = y


def layer_drag_end(x, y, button, modifiers):
        app.layerDragStartLayer = None
        app.layerDragStartX = None
        app.layerDragStartY = None


def main(filepath, machineNum):
    global blLabels
    global brLabels
    global tlLabels
    global trLabels
    
    global window
    
    global app
    
    global fpsLabel
    global layerLabel
    

    #### MAIN CODE ####
    print "Yet Another GCode Viewer v%s"%YAGV_VERSION

    import sys
    if len(sys.argv) > 1:
            path = sys.argv[1]
    else:
            # get the real path to the script
        #script_path = os.path.realpath(__file__)
            # get the containing folder
        #script_dir = os.path.dirname(script_path)
            # default to hana
        temp_dir = "C:\Users\Just\Desktop\Yet_Another_Gcode_Viewer\yagv-v0.3b\yagv"
        path = os.path.join(temp_dir, "20mmCube_export.gcode")
        path = filepath

    print "loading file..."
    t1 = time.time()
    app = App().run(path, machineNum)
    t2 = time.time()
    print "loaded file in %0.3f ms" % ((t2-t1)*1000.0, )


    window = MyWindow(None, None, "Yet Another GCode Viewer v%s"%YAGV_VERSION, True)

    # debug: log all events
    # window.push_handlers(pyglet.window.event.WindowEventLogger())

    # HUD labels
    blLabels = []
    brLabels = []
    tlLabels = []
    trLabels = []

    # help
    helpText = [    "Right-click & drag (any direction) to change layer",
                                    "Scroll to zoom",
                                    "Left-click & drag to rotate view"]
    for txt in helpText:
            blLabels.append(
                    pyglet.text.Label(      txt,
                                                            font_size=12) )

    # statistics
    # model stats
    statsLabel = pyglet.text.Label( "",
                                                                    font_size=12,
                                                                    anchor_y='top')
    filename = os.path.basename(path)
    statsLabel.text = "%s: %d segments, %d layers."%(filename, len(app.model.segments), len(app.model.layers)-2)

    # fps counter
    fpsLabel = pyglet.text.Label(   "",
                                                                    font_size=12,
                                                                    anchor_y='top')
    tlLabels.append(statsLabel)
    tlLabels.append(fpsLabel)

    # status
    # current Layer
    layerLabel = pyglet.text.Label( "layer %d"%(app.layerIdx-1),
                                                                    font_size=12,
                                                                    anchor_x='right', anchor_y='top')
    trLabels.append(layerLabel)

    # layout the labels in the window's corners
    window.placeLabels(window.width, window.height)
        
    @window.event
    def on_key_press(symbol, modifiers):
        if symbol == key.UP:
            app.layerIdx += 1
            # clamp layer to 0-max
            app.layerIdx = max(min(app.layerIdx, app.model.topLayer), 2)
            
            layerLabel.text = "layer %d"%(app.layerIdx-1)
        elif symbol == key.DOWN:
            app.layerIdx -= 1
            # clamp layer to 0-max
            app.layerIdx = max(min(app.layerIdx, app.model.topLayer), 2)
            
            layerLabel.text = "layer %d"%(app.layerIdx-1)
        if symbol == key.LEFT:
            app.layerIdx -= 5
            # clamp layer to 0-max
            app.layerIdx = max(min(app.layerIdx, app.model.topLayer), 2)
            
            layerLabel.text = "layer %d"%(app.layerIdx-1)
        elif symbol == key.RIGHT:
            app.layerIdx += 5
            # clamp layer to 0-max
            app.layerIdx = max(min(app.layerIdx, app.model.topLayer), 2)
            
            layerLabel.text = "layer %d"%(app.layerIdx-1)
    # render the model
    print "rendering vertices..."
    app.renderVertices()
    print "rendering indexed colors..."
    app.renderIndexedColors()
    print "rendering true colors..."
    app.renderColors()
    print "generating graphics..."
    app.generateGraphics()
    print "Done"
    pyglet.app.run()


#main()
#pyglet.app.run()
