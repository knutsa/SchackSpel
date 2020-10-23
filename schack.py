import sys
import os
import pygame
import glob
import random
SIZE = 640
pjas_namn = ("torn", "hast", "lopare", "drottning", "kung", "lopare", "hast", "torn")
vita, svarta = [], []
pjas_dict = {'v':vita, 's':svarta}
player_side = 'v'
bot1_side = 's'

is_legit = lambda x, y : 0<=x<8 and 0<=y<8

def get_rel_pos(pjas_typ):
    "Returns tuple of ranges/directions the type can go to."
    if not pjas_typ in pjas_namn and pjas_typ[:-2] != "bonde":
        raise ValueError("{0} is an invalid type of piece.".format(pjas_typ))
    if pjas_typ == "hast":
        return (((2,1),) ,((1,2),) ,((-1,2),) ,((-2,1),) ,((-2,-1),) ,((-1,-2),) ,((1,-2),) ,((2,-1),) )
    if pjas_typ == "kung":
        return (((-1,0),) , ((1,0),) , ((0,-1),) , ((0,1),) , ((-1,-1),) , ((1,1),) , ((1,-1),) , ((-1,1),) )  
    if pjas_typ == "bonde_v":
        return ( ((0,1),), )
    if pjas_typ == "bonde_s":
        return ( ((0,-1),), )

    rak_x1, rak_x2 = tuple((i,0) for i in range(1,8)), tuple((i,0) for i in range(-1,-8,-1))
    rak_y1, rak_y2 = tuple((0,i) for i in range(1,8)), tuple((0,i) for i in range(-1,-8,-1))
    diag_1, diag2 = tuple((i,i) for i in range(1,8)), tuple((i,i) for i in range(-1,-8,-1))
    diag_3, diag_4 = tuple((i,-i) for i in range(1,8)), tuple((i,-i) for i in range(-1,-8,-1))
    res = []

    if pjas_typ in ("torn", "drottning"):
        res.extend((rak_x1, rak_x2, rak_y1, rak_y2))
    if pjas_typ in ("lopare", "drottning"):
        res.extend((diag_1, diag2, diag_3, diag_4))
    return tuple(res)

def is_free(pos, grid, side, vita=vita, svarta=svarta):
    "Checks if a box is threatened by any piece"
    assert side in ("s", "v"), "Invalid side argument given: '{0}'".format(side)
    pjaser = (vita, svarta)[('s', 'v').index(side)]
    for pjas in (all_pjas for all_pjas in pjaser if grid[all_pjas.x][all_pjas.y].pjas is all_pjas):
        if pos in pjas.goes_to(grid, True):
            return False
    return True

def safe_move(pjas, pos, grid):
    "Checks if a piece can go to/be on a position without being threatened."
    grid[pjas.x][pjas.y].pjas = None
    res = is_free(pos, grid, pjas.side)
    grid[pjas.x][pjas.y].pjas = pjas
    return res

def is_valid_state(grid, side):
    assert  len(pjas_dict[side])>0, "Is_valid_state called from side without pieces."
    kung = pjas_dict[side][0].kung
    if is_free((kung.x, kung.y), grid, side):
        return True
    return False

def is_valid_move(start, to, grid, vita=vita, svarta=svarta):
    "Checks if a move is valid"
    x1, y1 = start
    moving = grid[x1][y1].pjas
    if not moving:
        return False
    side = moving.side
    old = moving.pos()
    killed = moving.move_to(to, grid, only_testing=True)
    was_valid = is_free(moving.kung.pos(), grid, moving.side)
    moving.move_to(old, grid, only_testing=True)
    if killed: #Restore the dead
        grid[killed.x][killed.y].pjas = killed

    return was_valid



class Pjas:
    size = 60
    moved = False
    kung = None
    img = None
    def __init__(self, adress, cord, pjas_typ, grid=None, pre_rel=None):
        "Inits pjas class. img-adress, cordinates(x,y), type of piece(pjasnamn/bonde_v/s), optional grid to edit grid[pos].pjas"      
        no_img = False
        if adress in ('s','v'):
            side = adress
            no_img = True
            self.side = side
        else:
            side = os.path.splitext(adress)[0][-1]
            self.side = side
            assert side in ('s', 'v'), "Adress {0} not pointing to chess piece".format(adress) 
            self.img = pygame.image.load(adress)
        self.x, self.y = cord
        self.typ = pjas_typ
        #relative postisions
        if pre_rel:
            self.rel = pre_rel
        else:
            self.rel = get_rel_pos(pjas_typ)
        if pjas_typ == "bonde_v":
            self.kill = ((1,1), (-1,1))
            self.bonus = (0,2)
        if pjas_typ == "bonde_s":
            self.kill = ((1,-1), (-1,-1))
            self.bonus = (0,-2)
        if grid:
            grid[self.x][self.y].pjas = self
    
    def pos(self):
        return (self.x, self.y)
    
    def blit(self, dis):
        "Draws image of itself."
        s = SIZE // 8
        margin = (s-self.size)//2
        x, y = self.x * s + margin, self.y*s+margin
        dis.blit(self.img, (x, y))
    
    def goes_to(self, grid, only_killing = False):
        "Creates generator to iterate through every square self can go to."
        for line in self.rel:  #Ordinary, goes through every direction this type of piece can go to.
            for rel_pos_x, rel_pos_y in line: #every square in this direction
                if only_killing and self.typ in ("bonde_s", "bonde_v"): continue
                x, y = self.x + rel_pos_x, self.y + rel_pos_y
                if not is_legit(x,y):
                    break
                at = grid[x][y].pjas
                if at != None:
                    if only_killing or (at.side != self.side and self.typ not in ("bonde_v", "bonde_s") ):
                        if only_killing or at.typ != "kung":
                            if only_killing or self.typ != "kung":
                                yield (x,y)
                            elif safe_move(self, (x,y), grid):  #king looking for move, not only_killing
                                yield (x,y)
                    break
                if self.typ != "kung" or only_killing :
                    yield (x,y)
                elif safe_move(self, (x,y), grid):
                    yield (x,y)


        if self.typ  in ("bonde_s", "bonde_v"):   #Special case pawn
            if not self.moved and not only_killing:  #First move go two steps.
                x,y = self.x + self.rel[0][0][0], self.y + self.rel[0][0][1]
                if not grid[x][y].pjas and not grid[self.x][self.y+self.bonus[1]].pjas:
                    yield (self.x,self.y+self.bonus[1])
            for rel_x, rel_y in self.kill:              #Go diagonally if it kills opponent
                target_x, target_y = self.x+rel_x, self.y + rel_y
                if not is_legit(target_x, target_y):
                    continue
                if grid[target_x][target_y].pjas:
                    if (grid[target_x][target_y].pjas.side != self.side and grid[target_x][target_y].pjas.typ != "kung") or only_killing:
                        yield (target_x, target_y)
                elif only_killing:
                    yield (target_x, target_y)
        if (self.typ == "kung"  )and (not self.moved and not only_killing): #castling
            for d in (-1,1):
                for i in (1,2):
                    if not is_free((self.x+i*d,self.y), grid, self.side) or grid[self.x+i*d][self.y].pjas:
                        break
                    if i == 2:
                        rook =  grid[(d+1)//2*7][self.y].pjas
                        if rook:
                            if not rook.moved:
                                yield (self.x+i*d, self.y)
            
    def die(self, grid, vita=vita, svarta=svarta):
        "Removes itself from grid and piece list when removed."
        grid[self.x][self.y].pjas = None
        l = (vita, svarta)[('v','s').index(self.side)]
        ind = l.index(self)
        del l[ind]

    def move_to(self, pos, grid, only_testing = False, vita=vita, svarta=svarta):
        "Moves piece to pos:(x,y) and edits the grid pjas attributes accordingly."
        tox, toy = pos
        killing = grid[tox][toy].pjas
        if grid[tox][toy].pjas and not only_testing:
            grid[tox][toy].pjas.die(grid)
        if self.typ == "kung" and abs(pos[0]-self.x)>1 and not only_testing: # castling
            self.castling(pos, grid)
        grid[self.x][self.y].pjas, grid[pos[0]][pos[1]].pjas = None, grid[self.x][self.y].pjas
        self.x, self.y = pos
        if not only_testing: self.moved = True
        if self.typ in ("bonde_v", "bonde_s") and not only_testing: #make new piece
            ind = ('s', 'v').index(self.side)
            if self.y == ind*7:
                self.transform()
        return killing
    
    def castling(self, pos, grid):
        d = (pos[0]-self.x)//abs(pos[0]-self.x)
        rook = grid[(d+1)//2*7][self.y].pjas
        rook_tox, rook_toy = pos[0]-d, self.y
        rook.move_to((rook_tox, rook_toy), grid)
    
    def transform(self):
        if self.side == player_side:
            new_type = input("Du kom med en bonde till sista linjen. Välj vilken pjäs du vill ha: ")
            while new_type not in ("hast", "lopare", "torn", "drottning"):
                new_type = input("Du måste ange en giltig pjäs. Välj 'hast', 'torn', 'lopare' eller 'drottning'. ")    
        else:
            new_type = bot.chose_piece()
        new_adress = glob.glob('*'+new_type+'_'+self.side+'*')[0]
        self.__init__(new_adress, (self.x, self.y), new_type)
    
 #   def __del__(self):
#        if self.img:
  #          print("{0} piece of {1} side died. ".format(self.typ, self.side))
    
    def copy(self):
        "Returns a new copied instance of itself."
        res = Pjas(self.side, self.pos(), self.typ, None, self.rel)
        res.moved = self.moved
        return res

        

class Ruta:
    def __init__(self):
        "Inits ruta class. Only attributes pjas and available(indicates if currently moving piece can go here)"
        self.pjas = None
        self.available = False

class Player:
    "Makes moves for the user."
    moving = None
    def __init__(self, pjaser):
        self.pjaser = pjaser
        self.side = pjaser[0].side
        for pjas in pjaser:
            if pjas.typ == 'kung':
                self.kung = pjas
                break
        for pjas in pjaser:
            pjas.kung = self.kung
        
    def begin_move(self, pos, grid):
        x, y = pos
        my_piece = grid[x][y].pjas
        if my_piece:
            if my_piece.side == self.side: #It's my piece
                self.moving = my_piece
                for tox, toy in my_piece.goes_to(grid):
                    if is_valid_move(my_piece.pos(), (tox, toy), grid):
                        grid[tox][toy].available = True
                return True
        return None

    def make_move(self, pos, grid):
        "Perfroms a move."
        x,y = pos
        if not self.moving:
            return None
        self.moving.move_to(pos, grid)
        self.moving = None
        return True

class Random_bot:
    "Plays random."
    kung = None
    def __init__(self, pjaser):
        self.pjaser = pjaser
        self.side = pjaser[0].side
        for pjas in pjaser:
            if pjas.typ == "kung":
                self.kung = pjas
        for pjas in pjaser:
            pjas.kung = self.kung

    def make_move(self, grid):
        "Makes a random valid chess move."
        pjaser = self.pjaser
        kung = self.kung
        op_side = ('s','v')[('s','v').index(self.side)*-1+1]        
        options = [pjas for pjas in pjaser]


        while options:
            choice = random.choice(options)
            pos_moves = [move for move in choice.goes_to(grid)]

            while pos_moves:
                move = random.choice(pos_moves)
                old = (choice.x, choice.y)
                if is_valid_move(choice.pos(), move, grid):
                    choice.move_to(move, grid)                  
                    return 0
                pos_moves.remove(move)

            options.remove(choice)
        if is_free((self.kung.x, self.kung.y), grid, self.side):
            return -1
        return 1

    def chose_piece():
        return random.choice(("torn", "hast", "lopare", "drottning"))

def ram(dis, pos, dim, width, color=(90,255,0)):
    "Draws empty rectangle. Takes pos:(x,y), dimension_of_rectangle:(length, height) and width_of_border."
    x, y, l, h = pos[0], pos[1], dim[0], dim[1]
    pygame.draw.rect(dis, color, [x,y,l,width]) #övre
    pygame.draw.rect(dis, color, [x,y,width,h]) #vänstra
    pygame.draw.rect(dis, color, [x,y+h-width,l,h]) #nedre
    pygame.draw.rect(dis, color, [x+l-width,y,width,h]) #högra

def draw_grid(dis, grid):
    ''' Ritar Brädet '''
    white = (255,255,255)
    black = (50,50,50)
    s = SIZE // 8
    for y in range(0,8):
        add = 1
        if y % 2 == 1:
            add = 0
        for x in range(0,8):
            if (x+add) % 2 == 0:  # Vit ruta
                pygame.draw.rect(dis, white, [x*s,y*s,s,s])
            else:    # Svart ruta
                pygame.draw.rect(dis, black, [x*s,y*s,s,s])
            if grid[x][y].pjas:
                grid[x][y].pjas.blit(dis)
            if grid[x][y].available:
                ram(dis, (x*s,y*s), (s,s), 10)


def main(opp = None):
    s = SIZE//8
    moving_from = (None, None)
    your_move = 0
    dis = pygame.display.set_mode((SIZE, SIZE))
    clock = pygame.time.Clock()
    going = True
    grid = global_grid #[[Ruta() for i in range(8)] for j in range(8)]
    #Skapa pjäser
    player = Player(pjas_dict[player_side])
    if opp:
        bot = opp
    else:
        bot = Random_bot(pjas_dict[bot1_side])
    if bot1_side == 'v':
        bot.make_move(grid)
      
    while going:
        draw_grid(dis, grid)
        pygame.display.update()
        if your_move: #bot playing
            your_move = bot.make_move(grid) # bot makes move
            if your_move:
                print(("Du van!!", "Patt!!")[(1,-1).index(your_move)])
            your_move = 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                going = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                #Get position
                x, y = event.pos
                x, y = x // s, y // s
                if not is_legit(x,y):
                    continue
                available = grid[x][y].available
               #Clear grid
                for line in grid:
                    for square in line:
                        square.available = False
                #Player makes move
                if your_move == 0:           
                    if available:
                        player.make_move((x,y), grid)
                        your_move = 1
                    else:
                        player.begin_move((x,y), grid)
        clock.tick(20)

os.chdir('/Users/Knut/.vscode/Python/Schack/pjaser')
global_grid = [[Ruta() for i in range(8)] for j in range(8)]
for i in range(0,8):
    list_adress_p1, list_adress_p2 = glob.glob("*"+pjas_namn[i]+"_V*"), glob.glob("*"+pjas_namn[i]+"_S*")
    p1 = Pjas(list_adress_p1[0], (i,0), pjas_namn[i], global_grid) 
    p2 = Pjas(list_adress_p2[0], (i,7), pjas_namn[i], global_grid)
    bonde1, bonde2 = Pjas(glob.glob("*bonde_V*")[0], (i,1), "bonde_v", global_grid), Pjas(glob.glob("*bonde_S*")[0], (i,6), "bonde_s", global_grid)
    vita.extend([p1, bonde1])
    svarta.extend([p2, bonde2])

if __name__ == "__main__":
    main()