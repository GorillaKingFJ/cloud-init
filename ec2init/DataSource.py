
import ec2init
import UserDataHandler as ud

class DataSource:
    userdata = None
    metadata = None
    userdata_raw = None

    def __init__(self):
       pass

    def get_userdata(self):
        if self.userdata == None:
            self.userdata = ud.preprocess_userdata(self.userdata_raw)
        return self.userdata

    def get_userdata_raw(self):
        return(self.userdata_raw)

    def get_public_ssh_keys(self):
        return([])
