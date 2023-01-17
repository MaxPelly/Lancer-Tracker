# An object for managing player manna in a lancer game
#     Copyright (C) 2021  Max Pelly

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see https://www.gnu.org/licenses/.


from tinydb import TinyDB, Query
from threading import Lock


    
class Player(object):
    licence_cost = 500
    talent_cost = 300
    training_cost = 200
    bought_12_error = "You may only buy 12 of each upgrade."
    no_money_error = "You don't have sufficient manna."
    
    lock = Lock()
    db = TinyDB("Players.json")
    
    def __init__(self,name, callsign="", manna=0, licences=0, talents=0, training=0, new=True, identity=None):
        if new:
            with Player.lock:
                self.id = Player.db.insert({'name':name, 'callsign':callsign, 'manna':manna, 'licences':licences, 'talents':talents, 'training':training})
        else:
            self.id = identity
            
    def __str__(self):
        data = self.get()
        callsign = data['callsign']
        manna = data['manna']
        manna_spent = self.get_manna_spent(data)
        licences = data['licences']
        talents = data['talents']
        training = data['training']
        ll = self.get_ll(data)
        
        return(f"{callsign} ll {ll}. {manna-manna_spent}/{manna} manna. {licences} licences. {talents} talents. {training} training.")
    
    
    @classmethod
    def get_player_by_name(cls, name, allow_make=False):
        player = Query()
        if data := Player.db.get(player.name==name):
            return Player(**data, identity=data.doc_id, new=False)
        
        if allow_make:
            return Player(name)
        
        return None
    
    @classmethod
    def show_all(cls):
        for player in Player.db:
            print(player)

        
    def _set_vals(self, **kwargs):
        with Player.lock:
            Player.db.update(kwargs, doc_ids=[self.id])
            
    def delete(self, confirm=False):
        if confirm:
            with Player.lock:
                Player.db.remove(doc_ids=[self.id])
                return True
        return False
    
    def update_callsign(self, callsign):
        self._set_vals(callsign=callsign)
    
    def get(self, key=None):
        if key:
            return Player.db.get(doc_id=self.id).get(key)
        else:
            return Player.db.get(doc_id=self.id)
        
    def get_manna_spent(self, data=None):
        if not data:
            data = self.get()
        return data['licences'] * Player.licence_cost + \
                data['talents'] * Player.talent_cost + \
                data['training'] * Player.training_cost
    
    def get_ll(self, data=None):
        return self.get_manna_spent(data)//1000
    
    def get_manna_left(self):
        data = self.get()
        return data["manna"] - self.get_manna_spent(data)
    
    def give_manna(self, ammount):
        manna = self.get('manna')        
        self._set_vals(manna=manna+ammount)
        
    def spend_manna(self, ammount):
        return(self.get_manna_left() >= ammount)
        
                
    def _buy(self, item):
        if item not in ["licences", "talents", "training"]:
            raise Exception()
            
        purchased = self.get(item)
        if purchased >= 12:
            return False, Player.bought_12_error
        
        if not self.spend_manna(Player.licence_cost):
            return False, Player.no_money_error
            
        self._set_vals(**{item:purchased+1})
        return True, purchased+1
    
    def buy_licence(self):
        return self._buy("licences")
    
    def buy_talent(self):
        return self._buy("talents")
    
    def buy_training(self):
        return self._buy("training")
        
