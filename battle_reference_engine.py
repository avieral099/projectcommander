import json


class BattleReference:
    def __init__(self):
        self.locked = False
        self.data = {}

    def lock(self, data):
        if self.locked:
            return False

        self.locked = True
        self.data = data

        with open("battle_reference.json", "w") as file:
            json.dump(self.data, file, indent=4)

        return True

    def show(self):
        return self.data
