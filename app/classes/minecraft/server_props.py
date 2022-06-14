import pprint
import os


class ServerProps:
    def __init__(self, filepath):
        self.filepath = filepath
        self.props = self._parse()

    def _parse(self):
        # Loads and parses the file specified in self.filepath
        with open(self.filepath, encoding="utf-8") as full_path:
            line = full_path.readline()
            dictionary = {}
            if os.path.exists(".header"):
                os.remove(".header")
            while line:
                if "#" != line[0]:
                    string = line
                    string1 = string[: string.find("=")]
                    if "\n" in string:
                        string2 = string[string.find("=") + 1 : string.find("\n")]
                    else:
                        string2 = string[string.find("=") + 1 :]
                    dictionary[string1] = string2
                else:
                    with open(".header", "a+", encoding="utf-8") as header:
                        header.write(line)
                line = full_path.readline()
        return dictionary

    def print(self):
        # Prints the properties dictionary (using pprint)
        pprint.pprint(self.props)

    def get(self):
        # Returns the properties dictionary
        return self.props

    def update(self, key, val):
        # Updates property in the properties dictionary [ update("pvp", "true") ]
        # and returns boolean condition
        if key in self.props.keys():
            self.props[key] = val
            return True
        return False

    def save(self):
        # Writes to the new file
        with open(self.filepath, "a+", encoding="utf-8") as f:
            f.truncate(0)
            with open(".header", encoding="utf-8") as header:
                line = header.readline()
                while line:
                    f.write(line)
                    line = header.readline()
                header.close()
            for key, value in self.props.items():
                f.write(key + "=" + value + "\n")
        if os.path.exists(".header"):
            os.remove(".header")

    @staticmethod
    def cleanup():
        if os.path.exists(".header"):
            os.remove(".header")
