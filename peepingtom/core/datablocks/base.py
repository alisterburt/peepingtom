from ...utils import AttributedList, listify


class DataBlock:
    """
    Base class for all simple and complex datablocks.
    Provides common methods and easy type inference
    """
    def __init__(self, name=None, depictor=None):
        if name is None:
            name = 'NoName'
        self.name = name
        self.depictor = depictor

    def updated(self):
        """
        this function is called when the data changed in order to trigger callbacks
        """
        if self.depictor is not None:
            self.depictor.update()

    def __newlike__(self, *args, **kwargs):
        # this makes sure that operators get the right output in case
        # _merge or _stack return notimplemented
        if args and args[0] is NotImplemented:
            return NotImplemented
        cls = type(self)
        return cls(*args, **kwargs)

    def __shape_repr__(self):
        return ''

    def __base_repr__(self):
        return f'{type(self).__name__}[{self.name}]{self.__shape_repr__()}'

    def __repr__(self):
        return f'<{self.__base_repr__()}>'

    def __and__(self, other):
        if isinstance(other, DataBlock):
            return DataCrate([self, other])
        elif isinstance(other, DataCrate):
            return DataCrate(self) + other
        else:
            return NotImplemented

    def __iand__(self, other):
        return NotImplemented

    @staticmethod
    def _merge_data(datablocks):
        """
        convenience method to merge the data of several datablocks
        of the same type into one, within the same ndimensional space
        used by merge and imerge.
        """
        return NotImplemented

    @staticmethod
    def _stack_data(datablocks):
        """
        convenience method to stack the data of several datablocks into one.
        If dimensionality is the same, add a new dimension; otherwise,
        use the next available dimension for the datablocks with smaller dimensionality
        used by stack and istack.
        """
        return NotImplemented

    def _merge(self, datablocks):
        """
        merge several datablocks and return a `newlike` object
        self is not part of merged objects
        """
        return NotImplemented

    def _stack(self, datablocks):
        """
        stack several datablocks and return a `newlike` object
        self is not part of stacked objects
        """
        return NotImplemented

    def _imerge(self, datablocks):
        """
        like merge, but inplace. Self is part of merged objects.
        """
        return NotImplemented

    def _istack(self, datablocks):
        """
        like stack, but inplace. Self is part of stacked objects.
        """
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, type(self)):
            return self._merge([self, other])
        else:
            return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, type(self)):
            self._imerge([other])
            return self
        else:
            return NotImplemented

    def __or__(self, other):
        if isinstance(other, type(self)):
            return self._stack([self, other])
        else:
            return NotImplemented

    def __ior__(self, other):
        if isinstance(other, type(self)):
            self._istack([other])
            return self
        else:
            return NotImplemented


class SimpleBlock(DataBlock):
    """
    Base class for all simple DataBlock objects, data types which can be visualised by Depictors

    SimpleBlock objects must implement a data setter method as _data_setter which returns
    the appropriately formatted data

    Calling __getitem__ on a SimpleBlock will call __getitem__ on its data property
    """
    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        if isinstance(data, type(self)):
            self._data = data.data
        else:
            self._data = self._data_setter(data)
        self.updated()

    def _data_setter(self, data):
        """
        takes raw data and returns it properly formatted to the SimpleBlock subclass specification.
        """
        raise NotImplementedError('SimpleBlocks must implement this method')

    def __setitem__(self, key, value):
        self.data.__setitem__(key, value)
        self.updated()

    def __getitem__(self, key):
        return self.__newlike__(self.data.__getitem__(key))

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        yield from self.data.__iter__()

    def __reversed__(self):
        yield from self.data.__reversed__()

    def _merge(self, datablocks):
        merged = self._merge_data(datablocks)
        if merged is NotImplemented:
            return NotImplemented
        return self.__newlike__(merged)

    def _stack(self, datablocks):
        stacked = self._stack_data(datablocks)
        if stacked is NotImplemented:
            return NotImplemented
        return self.__newlike__(self._stack_data(datablocks))

    def _imerge(self, datablocks):
        merged = self._merge_data([self] + datablocks)
        if merged is NotImplemented:
            return NotImplemented
        self.data = merged

    def _istack(self, datablocks):
        stacked = self._stack_data([self] + datablocks)
        if stacked is NotImplemented:
            return NotImplemented
        self.data = stacked


class MultiBlock(DataBlock):
    """
    Unites multiple SimpleBlocks into a more complex data object

    Note: classes which inherit from 'MultiBlock' should call super().__init__()
    first in their constructors so that references to blocks are correctly defined
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._blocks = []

    def __setattr__(self, name, value):
        """
        Extend the functionality of __setattr__ to automatically add datablocks to the
        'blocks' attribute of a 'MultiBlock' when set
        """
        if isinstance(value, SimpleBlock):
            self._add_block(value)
        super().__setattr__(name, value)

    @property
    def blocks(self):
        return self._blocks

    @blocks.setter
    def blocks(self, blocks):
        blocks = listify(blocks)
        for block in blocks:
            if not isinstance(block, SimpleBlock):
                raise ValueError(f'MultiBlocks can only be made of SimpleBlocks, not "{type(block)}"')
        self._blocks = blocks

    def _add_block(self, block):
        """
        Adds a block to an existing list of SimpleBlocks in a MultiBlock

        This is particularly useful when extending the functionality of an existing
        MultiBlock object by inheritance
        """
        self._blocks.append(block)

    def __getitem__(self, key):
        subslices = []
        for block in self.blocks:
            subslices.append(block.__getitem__(key))
        return self.__newlike__(*subslices)

    def __len__(self):
        lengths = [len(block) for block in self.blocks]
        if all(l == lengths[0] for l in lengths):
            return len(self.blocks[0])
        raise TypeError(f"object of type '{type(self)}' has no len()")

    @staticmethod
    def _merge_data(multiblocks):
        blocks_data = []
        blocks_all = [mb.blocks for mb in multiblocks]
        # cryptic loop example: datablock types in "blocks" (a, b, c),
        # this loops through the list [(a1, a2, ...), (b1, b2, ...), (c1, c2, ...)]
        # so this separates the components of a list of multiblocks into a lists of
        # simple datablocks of the same type
        for blocks_by_type in zip(*blocks_all):
            blocks_data.append(blocks_by_type[0]._merge_data(blocks_by_type))
        return blocks_data

    @staticmethod
    def _stack_data(multiblocks):
        blocks_data = []
        blocks_all = [mb.blocks for mb in multiblocks]
        # cryptic loop example: datablock types in "blocks" (a, b, c),
        # this loops through the list [(a1, a2, ...), (b1, b2, ...), (c1, c2, ...)]
        # so this separates the components of a list of multiblocks into a lists of
        # simple datablocks of the same type
        for blocks_by_type in zip(*blocks_all):
            blocks_data.append(blocks_by_type[0]._stack_data(blocks_by_type))
        return blocks_data

    def _merge(self, multiblocks):
        return self.__newlike__(*self._merge_data(multiblocks))

    def _stack(self, multiblocks):
        return self.__newlike__(*self._stack_data(multiblocks))

    def _imerge(self, multiblocks):
        new_data = self._merge_data([self] + multiblocks)
        for block, data in zip(self.blocks, new_data):
            block.data = data

    def _istack(self, multiblocks):
        new_data = self._stack_data([self] + multiblocks)
        for block, data in zip(self.blocks, new_data):
            block.data = data


class DataCrate(AttributedList):
    """
    A container for DataBlock objects which exist within the same n-dimensional reference space
    """
    def __init__(self, iterable_or_datablock=()):
        # recursively unpack the iterable into datablocks only
        def unpack(iterable):
            datablocks = []
            if isinstance(iterable, (list, tuple)):
                for item in iterable:
                    datablocks.extend(unpack(item))
            else:
                datablocks.append(iterable)
            return datablocks

        items = unpack(iterable_or_datablock)
        self._checktypes(items)
        super().__init__(items)

    @staticmethod
    def _checktypes(items):
        for item in items:
            if not isinstance(item, DataBlock):
                raise TypeError(f'DataCrate can only hold DataBlocks, not {type(item)}')

    def __add__(self, other):
        if isinstance(other, list):
            self._checktypes(other)
            return DataCrate(super().__add__(other))
        if isinstance(other, DataBlock):
            return self + DataCrate([other])
        else:
            return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, list):
            self._checktypes(other)
            super().__iadd__(other)
            return self
        if isinstance(other, DataBlock):
            super().__iadd__([other])
            return self
        else:
            return NotImplemented

    def __and__(self, other):
        if isinstance(other, (list, DataBlock)):
            return self + other
        else:
            return NotImplemented

    def __iand__(self, other):
        if isinstance(other, (list, DataBlock)):
            self += other
            return self
        else:
            return NotImplemented

    def __base_repr__(self):
        return f'{type(self).__name__}({len(self)})'

    def __repr__(self):
        return f'<{self.__base_repr__()}: [{", ".join([datablock.__base_repr__() for datablock in self])}]>'
