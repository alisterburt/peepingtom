import numpy as np

from .naparidepictor import NapariDepictor


class ParticleDepictor(NapariDepictor):
    def depict(self):
        pkwargs = {'size': 3}
        vkwargs = {'length': 10}

        self._make_points_layer(self.get_positions(),
                                name=f'{self.name} - particle positions',
                                properties=self.get_properties(),
                                **pkwargs)

        self._make_vectors_layer(self.get_orientations(),
                                 name=f'{self.name} - particle orientations',
                                 **vkwargs)

    def get_positions(self):
        return self.datablock.positions.as_zyx()

    def get_properties(self):
        return self.datablock.properties.data

    def get_orientations(self):
        # get positions and 'projection' vectors
        positions = self.datablock.positions.as_zyx()
        unit_z_rotated_order_xyz = self.datablock.orientations.oriented_vectors('z').reshape((-1, 3))
        unit_z_rotated_order_zyx = unit_z_rotated_order_xyz[:, ::-1]
        # attach appropriate higher dimensions indeces to vectors
        # TODO: make more general
        if self.datablock.positions.ndim > 3:
            padded = np.zeros_like(self.datablock.positions.data)
            padded[:, -3:] = unit_z_rotated_order_zyx
            unit_z_rotated_order_zyx = padded
        return np.stack([positions, unit_z_rotated_order_zyx], axis=1)

    @property
    def points(self):
        return self.layers[0]

    @property
    def vectors(self):
        return self.layers[1]

    def update(self):
        self.points.data = self.get_positions()
        self.points.properties = self.get_properties()
        self.vectors.data = self.get_orientations()
