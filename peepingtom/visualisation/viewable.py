"""
Viewable interfaces data classes to napari
"""

import numpy as np
import napari
from napari.components.layerlist import LayerList

from ..base import PointBlock, LineBlock, OrientationBlock, ImageBlock


class Viewable:
    """
    Base class for objects which are viewable in napari
    """
    def __init__(self, viewer=None, parent=None, name=''):
        self.viewer = viewer
        self.parent = parent
        self.name = name
        self.layers = LayerList()

    def peep(self, viewer=None):
        """
        creates a new napari viewer if not present or given
        peeps the contents of the Viewable
        """
        # create a new viewer if necessary
        if viewer is not None:
            self.viewer = viewer
        elif self.viewer is None:
            self.viewer = napari.Viewer(ndisplay=3)
        # random check to make sure viewer was not closed
        try:
            self.viewer.window.qt_viewer.actions()
        except RuntimeError:
            self.viewer = napari.Viewer(ndisplay=3)

    def hide(self, layers=None):
        """
        layer_id can be the index or name of a layer or a list of ids
        """
        if layers is None:
            layers = [l for l in self.layers]
        if not isinstance(layers, list):
            layers = [layers]
        for l in layers:
            if l in self.layers:
                self.viewer.layers.remove(l)
                self.layers.remove(l)

    def update(self, **kwargs):
        """
        reload data in the viewer
        """
        self.hide()
        self.show(**kwargs)


class VolumeViewer(Viewable):
    """
    display the contents of a DataBlock in napari and provide hooks between Peeper and Data
    """
    def __init__(self, data_block, **kwargs):
        super().__init__(**kwargs)
        self.data_block = data_block

    @property
    def particles(self):
        return [p for p in self.data_block if isinstance(p, Particles)]

    @property
    def particle_positions(self):
        return [p.coords for p in self.particles]

    @property
    def particle_vectors(self):
        return [p.ori_as_vectors() for p in self.particles]

    @property
    def particle_vectors_napari(self):
        stacked = []
        for coords, vectors in zip(self.particle_positions, self.particle_vectors):
            stacked.append(np.stack([coords, vectors], axis=1))
        return stacked

    @property
    def images(self):
        return [i for i in self.data_block if isinstance(i, Image)]

    @property
    def image_data(self):
        return [i.data for i in self.images]

    @property
    def image_shapes(self):
        return [i.shape for i in self.image_data]

    def show(self, viewer=None, point_kwargs={}, vector_kwargs={}, image_kwargs={}):
        super().show(viewer=viewer)

        pkwargs = {'size': 3}
        vkwargs = {'length': 10}
        ikwargs = {}

        pkwargs.update(point_kwargs)
        vkwargs.update(vector_kwargs)
        ikwargs.update(image_kwargs)

        for particles in self.particles:
            layer = self.viewer.add_points(particles.coords,
                                           name=f'{self.name} - particle positions',
                                           properties=particles.prop_as_dict(),
                                           **pkwargs)
            self.layers.append(layer)

        for vectors in self.particle_vectors_napari:
            layer = self.viewer.add_vectors(vectors,
                                            name=f'{self.name} - particle orientations',
                                            **vkwargs)
            self.layers.append(layer)

        for image in self.images:
            layer = self.viewer.add_image(image.data,
                                          name=f'{self.name} - image',
                                          **ikwargs)
            self.layers.append(layer)
