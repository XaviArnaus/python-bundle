from __future__ import annotations

PATH_SEPARATOR_CHAR = "."


class Dictionary:
    """Class to handle simple dictionary-based storage

    The value contribution for this class is the ability to
        reference the keys on the tree by paths like:
        "root_object.child_1.child_2.child_3"

    It includes the basic common API
    - get
    - get_all
    - set
    - delete

    Plus some extra
    - get_keys
    - get_parent
    - initialize_recursive


    :Authors:
        Xavier Arnaus <xavi@arnaus.net>

    """

    def __init__(self, content: dict = {}, path_separator_char=None) -> None:
        self._content = content
        self._separator = path_separator_char\
            if path_separator_char is not None else PATH_SEPARATOR_CHAR

    def _is_int(self, element: str) -> bool:
        """Check if the given element is an integer without converting it"""
        if element[0] in ('-', '+'):
            return element[1:].isdecimal()
        return element.isdecimal()

    def get(self, param_name: str = "", default_value: any = None) -> any:
        """
        Returns the value found in the given param_name path,
        otherwise default_value is returned
        """
        if param_name.find(self._separator) > 0:
            # bring it local so we can play with it
            local_content = self._content
            for item in param_name.split(self._separator):

                if self._is_int(item):
                    # It's an int, so it's meant to be the key of a list
                    item = int(item)

                    if isinstance(local_content, list) and\
                       item < len(local_content) and\
                       local_content[item] is not None:
                        # If exists and is not None we keep digging
                        local_content = local_content[item]
                    else:
                        # Otherwise we just return the default value
                        return default_value
                else:
                    if item in local_content and local_content[item] is not None:
                        # If exists and is not None we keep digging
                        local_content = local_content[item]
                    else:
                        # Otherwise we just return the default value
                        return default_value

            # When reaching the end of the path, we return the value at this point
            return local_content

        # In the case of a single item param_name, get directly from the content.
        return self._content[param_name] \
            if self._content and param_name in self._content \
            else default_value

    def get_all(self) -> dict:
        """Returns the whole internal dictionary"""
        return self._content

    def _is_out_of_range(self, index: int, list_to_check: list) -> bool:
        """Checks if the given index is out of range for the given list"""
        try:
            list_to_check[index]
            return False
        except IndexError:
            return True

    def __recursive_set(self, param_name: str, value: any, dictionary: any = None) -> None:
        """
        Recursively walks through the dictionary to find the key to set, and sets it

        Raises a RuntimeError if any of the keys in the param_name does not exist
        Raises a ValueError if a key from the param_name is an index but the parent is
            not a list.
        """
        if param_name.find(self._separator) > 0:
            pieces = param_name.split(self._separator)

            if self._is_int(pieces[0]):
                item = int(pieces[0])

                # The dictionary argument must be a list. Complain otherwise.
                if not isinstance(dictionary, list):
                    raise ValueError(
                        f"With the key [{param_name}] I expect the parent to be a list," +
                        f" but its [{type(dictionary)}]"
                    )

                if item < len(dictionary) and dictionary[item] is not None:
                    self.__recursive_set(
                        param_name=self._separator.join(pieces[1:]),
                        value=value,
                        dictionary=dictionary[item]
                    )
                else:
                    raise RuntimeError(
                        f"Dictionary path [{item}] is out of bounds for [{dictionary}]"
                    )
            elif isinstance(dictionary, dict):
                # The dictionary argument is a dict
                if pieces[0] not in dictionary:
                    raise RuntimeError(
                        f"Dictionary key [{pieces[0]}] is unknown in [{dictionary}]"
                    )

                self.__recursive_set(
                    param_name=self._separator.join(pieces[1:]),
                    value=value,
                    dictionary=dictionary[pieces[0]]
                )
            else:
                # The dictionary argument is anything but a list or a dict
                raise RuntimeError(f"Dictionary path [{param_name}] unknown in [{dictionary}]")
        else:
            if self._is_int(param_name):
                # It's an int, so it's meant to be the key of a list
                param_name = int(param_name)

                # The dictionary must be a list. Complain otherwise.
                if not isinstance(dictionary, list):
                    raise ValueError(
                        f"With the key [{param_name}] I expect the parent to be a list," +
                        f" but its [{type(dictionary)}]"
                    )

                if param_name < len(dictionary):
                    # Normal set. Possibly an overwrite.
                    dictionary[param_name] = value
                else:
                    # So it is an append or a set out of bounds
                    #   Let's fill with None until the desired index
                    for idx in range(0, param_name + 1):
                        if not self._is_out_of_range(idx, dictionary):
                            continue
                        else:
                            dictionary.append(value if idx == param_name else None)
            else:
                if dictionary is not None:
                    dictionary[param_name] = value
                else:
                    dictionary = {param_name: value}

    def set(self, param_name: str, value: any = None):
        """
        Sets the given value into the given param_name path.

        If the final key's parent does not exist, it sets it new
        If the final key's parent exists and is a dict, it adds a new key with the value
        If the final key's parent exists and is not a dict, overwrites it with a dict
            consisting of the new key with the value

        Raises a RuntimeError if any of the keys in the param_name does not exist
        Raises a ValueError if a key from the param_name is an index but the parent is
            not a list.
        """
        if param_name is None:
            raise RuntimeError("Params must have a name")

        self.__recursive_set(param_name=param_name, value=value, dictionary=self._content)

    def key_exists(self, param_name: str) -> bool:
        """Checks if the given param_name path exists, including the indexes inside the list ranges"""
        key_to_search = self._get_focused_key(param_name=param_name)
        parent_object = self.get_parent(param_name)

        if parent_object is None:
            return False

        if isinstance(parent_object, list) and self._is_int(key_to_search):
            if self._is_out_of_range(int(key_to_search), parent_object):
                return False
            else:
                return True

        if isinstance(parent_object, dict):
            return True if key_to_search in parent_object else False

        return False

    def _get_focused_key(self, param_name: str) -> str:
        """Returns the last key of the param_name"""
        return param_name.split(self._separator)[-1]\
            if param_name.find(self._separator) > 0 else param_name

    def get_parent(self, param_name: str) -> dict:
        """Returns the parent object of the given param_name path"""
        if param_name.find(self._separator) > 0:
            pieces = param_name.split(self._separator)
            parent_key = self._separator.join(pieces[:-1])
            return self.get(param_name=parent_key, default_value=None)
        else:
            return self._content

    def delete(self, param_name: str) -> None:
        """Deletes the given param_name path key"""
        if self.key_exists(param_name=param_name):
            parent = self.get_parent(param_name=param_name)
            key_to_delete = self._get_focused_key(param_name=param_name)

            if isinstance(parent, list) and self._is_int(key_to_delete):
                key_to_delete = int(key_to_delete)

            del parent[key_to_delete]
            return True
        else:
            return False

    def initialise_recursive(self, param_name: str) -> None:
        """
        Walks through the given param_name path and creates all missing keys and dicts.

        Raises RuntimeError if a key of the param_name path already exists and it's not
            a dictionary or a list (whatever expected), to avoid overwriting.
        """
        pieces = param_name.split(self._separator)
        parent_path = ""
        # We start assuming that self._content is already {}
        for piece in pieces:
            path = f"{parent_path}{piece}"
            if not self.key_exists(path):
                parent = self.get_parent(path)
                if (isinstance(parent, dict) and not self._is_int(piece)) or\
                   (isinstance(parent, list) and self._is_int(piece)):
                    self.set(path, {})
                else:
                    # We can't create children on non-dict/non-list values,
                    #   and we won't overwrite current values
                    # This only applies to keysthat are in the middle of the path
                    #   as we're expected to go deep and we actually can't.
                    raise RuntimeError(
                        f"The key {parent_path[:-1]} " +
                        "already exists as a non-dict or non-list. " + "I won't overwrite."
                    )

            parent_path = f"{path}{self._separator}"

    def get_keys_in(self, param_name: str = None) -> list:
        """Returns the keys on the given param_name path dict"""
        if param_name is not None:
            obj = self.get(param_name=param_name)
        else:
            obj = self._content

        if isinstance(obj, dict):
            return [key for key in obj.keys()]
        if isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, set):
            return [key for key in range(len(obj))]
        else:
            return None

    def to_dict(self) -> dict:
        """Shortcut to get_all()"""
        return self.get_all()
    

    # @staticmethod
    # def merge(origin: Dictionary, destination_path: str = None) -> None:
    #     """
    #     Takes 
    #     """
