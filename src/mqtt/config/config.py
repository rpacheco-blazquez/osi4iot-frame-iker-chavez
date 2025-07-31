import os
import json


class Config:
    def __init__(self, configPath):
        print(configPath)
        configPathAbs = __file__.replace(os.path.basename(__file__), "") + configPath
        # Opening JSON file
        with open(configPathAbs, "r") as openfile:
            # Reading from json file
            configJSON = json.load(openfile)

        self.broker = (
            f"mqtt.{configJSON['broker']}"
            if configJSON.get("isCluster")
            else configJSON["broker"]
        )

        self.hashes = configJSON["hashes"]
        self.client_id = configJSON["client_id"]
        self.connectCerts = configJSON["connectCerts"]
        self.username = configJSON["username"]
        self.password = configJSON["password"]
        self.certs = {
            "ca_certs": __file__.replace(os.path.basename(__file__), "")
            + configJSON["ca_crt"],
            "certfile": __file__.replace(os.path.basename(__file__), "")
            + configJSON["group_1_crt"],
            "keyfile": __file__.replace(os.path.basename(__file__), "")
            + configJSON["group_1_key"],
        }
        self.topic = type("", (), {})()
        self.topic.subscribe = self.topicList(self.hashes["subscribe"], "subscribe")
        self.topic.publish = self.topicList(self.hashes["publish"], "publish")
        self.topic.pub_sub = self.topicList(self.hashes["pub/sub"], "pub/sub")

    def topicList(self, list, category=""):
        outputList = {}
        for i in list:
            topic = (
                f"{list[i]['type']}/Group_{list[i]['group']}/Topic_{list[i]['topic']}"
            )
            print(category + " - " + i + " : " + topic)
            outputList[i] = topic
        return outputList