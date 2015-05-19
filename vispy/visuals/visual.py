# -*- coding: utf-8 -*-
# Copyright (c) 2014, Vispy Development Team.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

from __future__ import division

from ..util.event import EmitterGroup, Event
from .shaders import StatementList
from .. import gloo

"""
API Issues to work out:

  * Need Visual.bounds() as described here:
    https://github.com/vispy/vispy/issues/141

"""


class Visual(object):
    """
    Abstract class representing a drawable object.

    At a minimum, Visual subclasses should extend the draw() method. 

    Events:

    update : Event
        Emitted when the visual has changed and needs to be redrawn.
    bounds_change : Event
        Emitted when the bounds of the visual have changed.

    Notes
    -----
    -   When used in the scenegraph, all Visual classes are mixed with
    vispy.scene.Node in order to implement the methods, attributes and
    capabilities required for their usage within it.
    """

    def __init__(self):
        self._visible = True
        self.events = EmitterGroup(source=self,
                                   auto_connect=True,
                                   update=Event,
                                   bounds_change=Event,
        )
        self._gl_state = {'preset': None}
        self._filters = set()
        self._hooks = {}

    def set_gl_state(self, preset=None, **kwargs):
        """Completely define the set of GL state parameters to use when drawing
        this visual.
        """
        self._gl_state = kwargs
        self._gl_state['preset'] = preset

    def update_gl_state(self, *args, **kwargs):
        """Modify the set of GL state parameters to use when drawing
        this visual.
        """
        if len(args) == 1:
            self._gl_state['preset'] = args[0]
        elif len(args) != 0:
            raise TypeError("Only one positional argument allowed.")
        self._gl_state.update(kwargs)

    def _update(self):
        """
        This method is called internally whenever the Visual needs to be 
        redrawn. By default, it emits the update event.
        """
        self.events.update()

    def draw(self, transforms):
        """
        Draw this visual now.
        The default implementation calls gloo.set_state().
        
        This function is called automatically when the visual needs to be drawn
        as part of a scenegraph, or when calling 
        ``SceneCanvas.draw_visual(...)``. It is uncommon to call this method 
        manually.
        
        The *transforms* argument is a TransformSystem instance that provides 
        access to transforms that the visual
        may use to determine its relationship to the document coordinate
        system (which provides physical measurements) and the framebuffer
        coordinate system (which is necessary for antialiasing calculations). 
        
        Vertex transformation can be done either on the CPU using 
        Transform.map(), or on the GPU using the GLSL functions generated by 
        Transform.shader_map().
        """
        gloo.set_state(**self._gl_state)

    def bounds(self, mode, axis):
        """ Return the (min, max) bounding values describing the location of
        this node in its local coordinate system.
        
        Parameters
        ----------
        mode : str
            Describes the type of boundary requested. Can be "visual", "data",
            or "mouse".
        axis : 0, 1, 2
            The axis along which to measure the bounding values, in
            x-y-z order.
        
        Returns
        -------
        None or (min, max) tuple. 
        
        Notes
        -----
        This is used primarily to allow automatic ViewBox zoom/pan.
        By default, this method returns None which indicates the object should 
        be ignored for automatic zooming along *axis*.
        
        A scenegraph may also use this information to cull visuals from the
        display list.
        
        """
        return None

    def update(self):
        """
        Emit an event to inform listeners that this Visual needs to be redrawn.
        """
        self.events.update()

    def _get_hook(self, shader, name):
        """Return a FunctionChain that Filters may use to modify the program.
        
        *shader* should be "frag" or "vert"
        *name* should be "pre" or "post"
        """
        assert name in ('pre', 'post')
        key = (shader, name)
        if key in self._hooks:
            return self._hooks[key]

        prog = getattr(self, '_program', None)
        if prog is None:
            raise NotImplementedError("%s shader does not implement hook '%s'"
                                      % key)
        hook = StatementList()
        if shader == 'vert':
            prog.vert[name] = hook
        elif shader == 'frag':
            prog.frag[name] = hook
        self._hooks[key] = hook
        return hook

    def attach(self, filter):
        """Attach a Filter to this visual. 
        
        Each filter modifies the appearance or behavior of the visual.
        """
        filter._attach(self)
        self._filters.add(filter)

    def detach(self, filter):
        """Detach a filter.
        """
        self._filters.remove(filter)
        filter._detach(self)
