import random

class RouletteGame():   
    RED_NUMBERS = {"1","3","5","7","9","12","14","16","18","19","21","23","25","27","30","32","34","36"}
    POCKETS = [str(n) for n in range(37)] + ["00"]
    
    def __init__(self):
        self.wheel_values = {n: self.wheel_color(n) for n in self.POCKETS}
    
    def wheel_color(self, n):
            if n in ("0","00"):
                return "green"
            return "red" if n in self.RED_NUMBERS else "black"
        
    # Function to handle bet types
    async def play_game(self, bet_type: str):
        # Get number and color of where the ball lands
        number, color = random.choice(list(self.wheel_values.items()))
        
        if number in ["0", "00"]:
            winner = False
        elif bet_type == "red" and color == "red":
            winner = True
        elif bet_type == "black" and color == "black":
            winner = True
        elif bet_type == "odd" and int(number) % 2 == 1:
            winner = True
        elif bet_type == "even" and int(number) % 2 == 0:
            winner = True
        else:
            winner = False
            
        return winner, number, color
        
    
    
        
    
    
    