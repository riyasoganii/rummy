import os
import pygame
from pygame.locals import *
from pygame.compat import geterror
from enum import Enum
from itertools import product
import random
from random import shuffle
import operator

if not pygame.font: print('Warning: fonts disabled')
if not pygame.mixer: print('Warning: sound disabled')

screen_width = 900
screen_height = 500


class Suit(Enum):
    CLUB = 1
    DIAMOND = 2
    HEART = 3
    SPADE = 4

    def __lt__(self, other):
        if not isinstance(other, Suit):
            return NotImplemented
        else:
            return self.value < other.value


class CardRank(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    def __lt__(self, other):
        if not isinstance(other, CardRank):
            return NotImplemented
        else:
            return self.value < other.value

    def __sub__(self, other):
        if not isinstance(other, CardRank):
            return NotImplemented
        else:
            return self.value - other.value


# joker ???

class Card(pygame.sprite.Sprite):
    offset = 20

    def __init__(self, s, v):
        pygame.sprite.Sprite.__init__(self)  # initialize sprite
        self.suit = s
        self.rank = v

        # load image
        if (self.rank.value <= 9):
            filename = str(self.rank.value) + self.suit.name[0].lower() + ".gif"
        else:
            filename = str(self.rank.name[0].lower()) + self.suit.name[0].lower() + ".gif"
        self.image, self.rect = load_image(filename, -1)

    def __str__(self):
        return str(self.rank.name) + "_" + str(self.suit.name)

    def eq(self, other):
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.rank == other.rank

    def __sub__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        else:
            return self.rank - other.rank


class Deck(pygame.sprite.Sprite):
    def __init__(self, name, image_file, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.cards = []
        self.name = name
        self.image, self.rect = load_image(image_file, -1)
        self.rect.x = x
        self.rect.y = y

    def __str__(self):
        str_val = self.name + "(" + str(len(self.cards)) + "): "
        for c in self.cards:
            str_val = str_val + str(c) + " "
        return str_val

    def load_image(self, filename):
        # load image
        self.image, self.rect = load_image(filename, -1)

    def deck_size(self):
        return len(self.cards)

    def shuffle_cards(self):
        shuffle(self.cards)

    def draw_cards(self, n):
        hand = []
        assert (n > 0)
        i = 0
        while (i < n):
            hand.append(self.cards[0])
            self.cards.pop(0)
            i += 1
        return hand

    def add_card(self, card):
        self.cards.insert(self, 0, card)


class DoubleDeck(Deck):
    def __init__(self, name, image_file, x, y):
        Deck.__init__(self, name, image_file, x, y)
        for i in range(2):
            for s, v in product(Suit, CardRank):
                self.cards.append(Card(s, v))


class Button(pygame.sprite.Sprite):
    def __init__(self, image_file, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image, self.rect = load_image(image_file, -1)
        self.rect.x = x
        self.rect.y = y


class GroupButton(Button):
    def __init__(self, x, y):
        Button.__init__(self, "groupgrey.gif", x, y)
        self.grey = True

    def update(self):
        if (self.grey):
            self.grey = False
            # make button green
            green_color = 0, 150, 0
            self.image, self.rect = load_image("group.gif", -1)
        else:
            self.grey = True
            # restore grey button
            grey_color = 85, 85, 85
            self.image, self.rect = load_image("groupgrey.gif", -1)
        self.rect.x, self.rect.y = screen_width - 125, screen_height - 250

    def clicked_in(self):
        if (self.rect.collidepoint(pygame.mouse.get_pos())):
            return True
        else:
            return False


class CGroupType():
    PURE_SEQ = 1
    IMPURE_SEQ = 2
    SET = 3
    UNKNOWN = 4


class CGroupStatus():
    INCOMPLETE = 1
    COMPLETE = 2


class CGroup():
    maxsize = 4

    def __init__(self, type):
        self.cards = []
        self.type = type
        self.status = CGroupStatus.INCOMPLETE

    def append(self, card):
        # if (len(self.cards) == self.maxsize):
        #    return False
        # else:
        self.cards.append(card)
        # if (len(self.cards) == self.maxsize):
        #    self.status = CGroupStatus.COMPLETE
        # return True

    def prepend(self, card):
        # if (len(self.cards) == self.maxsize):
        #    return False
        # else:
        self.cards.insert(0, card)

    #    if (len(self.cards) == self.maxsize):
    #        self.status = CGroupStatus.COMPLETE
    #    return True

    def __repr__(self):
        str_val = "["
        for c in self.cards:
            str_val += str(c) + " "
        str_val += "]"
        return str_val

    def size(self):
        return len(self.cards)


class Player():
    def __init__(self, deck, name):
        self.turn = False
        self.name = name
        self.cardgroups = []
        # get a hand
        self.cards = deck.draw_cards(13)
        new_group = CGroup(CGroupType.UNKNOWN)
        new_group.cards = self.cards
        self.cardgroups.append(new_group)

    def __str__(self):
        str_val = self.name + ": "
        for cg in self.cardgroups:
            for c in cg.cards:
                str_val = str_val + str(c) + " "
        return str_val

    def swap_cards(self, ix1, ix2):
        self.cards[ix1], self.cards[ix2] = self.cards[ix2], self.cards[ix1]


class Me(Player):

    # set some flags: have_4, have_pure_seq

    def __init__(self, deck, name):
        Player.__init__(self, deck, name)
        self.groups_ready = []
        self.groups_in_progress = []
        self.loose_cards = []
        self.jokers = []
        self.have_pure_seq = False

        # arrange cards by color and number
        self.cards.sort(key=operator.attrgetter("suit", "rank"))

        # make groups
        self.make_groups()

        # update groups with joker
        for j in self.jokers:
            self.update_groups(j)

    def make_groups(self):
        # iterate over all elements and group into pure sequences
        for cur_card in self.cards:
            # if cur_card is joker, add it to self.jokers

            if (self.cards.index(cur_card) == 0):
                new_group = CGroup(CGroupType.PURE_SEQ)
                new_group.append(cur_card)
            else:
                prev_card = self.cards[self.cards.index(cur_card) - 1]
                if (prev_card.suit == cur_card.suit):
                    if (cur_card.rank - prev_card.rank != 1):
                        self.cardgroups.append(new_group)
                        new_group = CGroup(CGroupType.PURE_SEQ)
                    if (not new_group.append(cur_card)):
                        CGroup.maxsize = 3  # one pure sequence has been made
                        self.have_pure_seq = True
                        new_group = CGroup(CGroupType.PURE_SEQ)
                        new_group.append(cur_card)

        # append last group
        self.cardgroups.append(new_group)

        # iterate over loose cards, and try to make sets

        # for each card in the joker list, call update_groups(card, true)

        print(self.cardgroups)

    def update_groups(self, card, isjoker=False):
        """
        for each group:
            try_to_add_card(group, card, isJoker)

        """

    def take_turn(self, closedeck, opendeck):
        if (opendeck.deck_size()):
            new_card = opendeck[len(opendeck) - 1]
            ret_val, throw_card = check(new_card)
            if (ret_val or throw_card):
                return ret_val, throw_card

        # get new card
        new_card = closedeck.draw_cards(1)

        # do I want this card?

    def try_to_add_card(self, group, card, isJoker):
        if (group.type == CGroupType.SET):
            try_to_add_card_to_set(group, card, isJoker)
        else:
            try_to_add_card_to_seq(group, card, isJoker)

    def try_to_add_card_to_seq(self, group, card, isJoker):
        # try to add non-joker card to a complete seq
        if (group.status == CGroupStatus.COMPLETE):
            if (group.type == CGroupType.PURE_SEQ or isJoker):
                return
            else:
                # look for joker and try to replace with true match
                for c in group.cards:
                    if (c == joker):
                        if (group.cards.index(c) == 0):
                            next_card = group.cards[group.cards.index(c) + 1]
                            if (next_card.rank - card.rank == 1):
                                group.cards[group.cards.index(c)] = card
                                # check and reset group type ???
                                return c
                        else:
                            prev_card = group.cards[group.cards.index(c) - 1]
                            if (card.rank - prev_card.rank == 1):
                                group.cards[group.cards.index(c)] = card
                                # check and reset group type ???
                                return c
        else:
            if (card is joker):
                group.append(card)
                group.type = CGroupType.IMPURE_SEQ
            else:
                if (card.rank() - group.cards[0].rank() == 1):
                    group.cards.prepend(card)
                    # check and reset group type ???
                elif (group.cards[-1].rank - card.rank() == 1):
                    group.cards.append(card)
                    # check and reset group type ???

    def try_to_add_card_to_set(self, group, card, isJoker):
        pass


class You(Player):
    def __init__(self, deck, name):
        Player.__init__(self, deck, name)

    def pick_card(self, deck):
        # get new card
        return deck.draw_cards(1)

    def add_card(self, ix, card):
        if (len(self.cards) > 13):
            return False
        else:
            self.cards.insert(ix, card)
            return True

    def rem_card(self, ix):
        if (len(self.cards) < 13):
            return False, None
        else:
            return True, self.cards.pop(ix)

    def throw_card(self, deck, card):
        deck.add_card(card)

    def reassign_card_locations(self):
        xpos = 10
        ypos = screen_height - 150
        for cg in self.cardgroups:
            assign_cards_location(cg.cards, xpos, ypos)
            xpos = cg.cards[-1].rect.right + 60

    def get_all_cards(self):
        all_cards = []
        for cg in self.cardgroups:
            all_cards.append(cg.cards)
        return all_cards

    def make_group(self, card_indices):
        new_group = CGroup(CGroupType.UNKNOWN)
        for i in range(0, len(card_indices), 2):
            gix = card_indices[i]
            cix = card_indices[i + 1]
            new_group.append(self.cardgroups[gix].cards[cix])
        for i in range(0, len(card_indices), 2):
            gix = card_indices[i]
            cix = card_indices[i + 1]
            self.cardgroups[gix].cards.pop(cix)

        self.cardgroups.append(new_group)
        self.reassign_card_locations()

    def clicked_in_group(self, cg):
        return_val = False
        mouse_pos = pygame.mouse.get_pos()
        i = -1
        group_rect = pygame.Rect(cg.cards[0].rect.x, cg.cards[0].rect.y, cg.cards[-1].rect.right - cg.cards[0].rect.x,
                                 cg.cards[-1].rect.bottom - cg.cards[0].rect.y)
        if (group_rect.collidepoint(mouse_pos)):
            return_val = True
            for c in cg.cards:
                i += 1
                c_rect = pygame.Rect(c.rect.x, c.rect.y, c.offset, c.rect.bottom - c.rect.top)
                if (c_rect.collidepoint(mouse_pos)):
                    break
        return return_val, i

    def clicked_in_hand(self):
        return_val = False
        mouse_pos = pygame.mouse.get_pos()
        i = -1
        j = -1
        for cg in self.cardgroups:
            i += 1
            return_val, j = self.clicked_in_group(cg)
            if return_val:
                break
        return return_val, i, j


main_dir = os.path.split(os.path.abspath(__file__))[0]
data_dir = os.path.join(main_dir, "data")


def load_image(name, colorkey=None):
    fullname = os.path.join(data_dir, name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error:
        print('Cannot load image:', fullname)
        raise SystemExit(str(geterror()))
    image = image.convert()
    if colorkey is not None:
        if colorkey is -1:
            colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey, RLEACCEL)
        return image, image.get_rect()


"""

def load_sound(name):
    class NoneSound:
        def play(self): pass
    if not pygame.mixer or not pygame.mixer.get_init():
        return NoneSound()
    fullname = os.path.join(data_dir, name)
    try:
        sound = pygame.mixer.Sound(fullname)
    except pygame.error:
        print ('Cannot load sound: %s' % fullname)
        raise SystemExit(str(geterror()))
    return sound"""


def assign_cards_location(cardslist, xpos, ypos):
    for c in cardslist:
        c.rect.x, c.rect.y = xpos, ypos
        xpos += Card.offset


def main():
    # initialize

    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption('Rummy')
    pygame.mouse.set_visible(1)

    # create background
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((0, 150, 0))

    # initialize objects
    stop_button = Button("stop.gif", screen_width - 100, screen_height - 450)
    print(stop_button.rect)
    declare_button = Button("declare.gif", screen_width - 125, screen_height - 350)
    group_button = GroupButton(screen_width - 125, screen_height - 250)

    closedeck = DoubleDeck("cd", "b.gif", screen_width - 800, screen_height - 450)
    closedeck.shuffle_cards()
    print(closedeck)

    opendeck = Deck("od", "holder.jpg", screen_width - 400, screen_height - 450)
    print(opendeck)

    temphold = Deck("th", "holder.jpg", screen_width - 600, screen_height - 300)

    me = Me(closedeck, "Me")
    print(me)

    user = You(closedeck, "User")
    print(user)

    print(closedeck.deck_size())

    # draw jokers
    joker1 = closedeck.draw_cards(1)
    joker1[0].image = pygame.transform.rotate(joker1[0].image, 90)
    joker1[0].rect.x, joker1[0].rect.y = closedeck.rect.x - 30, closedeck.rect.y + 26
    print("joker1: " + str(joker1[0]))
    joker2 = closedeck.draw_cards(1)
    joker2[0].image = pygame.transform.rotate(joker2[0].image, 90)
    joker2[0].rect.x, joker2[0].rect.y = closedeck.rect.x - 30, closedeck.rect.y + 6
    print("joker2: " + str(joker2[0]))
    print(closedeck.deck_size())

    # create sprite groups
    non_changing_sprites = pygame.sprite.Group((stop_button, declare_button, joker1[0], joker2[0]))
    changing_sprites = pygame.sprite.Group(closedeck, opendeck, temphold, group_button)

    # assign location to each user card and add to changing_sprites group
    assign_cards_location(user.cards, screen_width - 700, screen_height - 150)
    hand_sprite = pygame.sprite.Group(user.cards)

    # display the background and sprites
    screen.blit(background, (0, 0))
    non_changing_sprites.draw(screen)
    changing_sprites.draw(screen)
    hand_sprite.draw(screen)
    pygame.display.flip()

    clock = pygame.time.Clock()

    # start game
    print("Start when ready!")

    # main loop
    going = True
    user.turn = True
    temp_hold_full = False
    new_card = None
    cards_to_group = []
    group_enabled = False
    selected_card = None
    while going:
        # 60 frames per sec
        clock.tick(60)

        # handle events
        if (user.turn):
            for event in pygame.event.get():
                if event.type == QUIT:
                    # do you really want to exit?
                    going = False
                elif event.type == MOUSEBUTTONDOWN:
                    clicked_hand, group_ix, card_ix = user.clicked_in_hand()
                    if (clicked_hand):
                        print("Clicked card %d,%d" % (group_ix, card_ix))
                        if (new_card):
                            # insert new_card in hand
                            new_card = None
                            # redisplay cards
                        if (pygame.key.get_mods() & KMOD_RCTRL or pygame.key.get_mods() & KMOD_LCTRL):
                            cards_to_group.append(group_ix)
                            cards_to_group.append(card_ix)
                            if (len(cards_to_group) == 4):
                                group_enabled = True
                                group_button.update()
                        else:
                            # get ready to throw or group
                            if (group_enabled):
                                group_enabled = False
                                cards_to_group.clear()
                                # grey out group button
                                group_button.update()
                            cards_to_group.append(group_ix)
                            cards_to_group.append(card_ix)
                    elif (group_button.clicked_in()):
                        if (group_enabled):
                            # redraw cards grouping selected cards
                            user.make_group(cards_to_group)
                            hand_sprite.empty()
                            hand_sprite.add(user.get_all_cards())
                    elif (group_enabled):
                        group_enabled = False
                        cards_to_group.clear()
                        group_button.update()  # grey out button

                    """elif (clicked in closedeck)
                        if (selected_card):
                            selected_card = None
                        if (len(cards_to_group)):
                            start_grouping = False
                            group_enabled = False
                            cards_to_group.clear()
                            redraw cards
                            grey out group button
                        if (you.deck_size() == 13 and not temp_hold_full)  # this prevents extra drawing of card
                            new_card = sd.draw_card(1)
                            display new_card in temp_hold
                            temp_hold_full = True
                    elif (clicked in temp_hold)
                        if (selected_card):
                            selected_card = None
                        if (len(cards_to_group)):
                            start_grouping = False
                            group_enabled = False
                            cards_to_group.clear()
                            redraw cards
                            grey out group button
                        if (temp_hold != None):
                            # get ready to add to hand
                            new_card = card
                            highlight temp_hold
                    elif (clicked in STOP):
                    elif (clicked in SHOW):                        
                    elif (clicked in opendeck):
                        if (selected_card):
                            if (you.deck_size() == 14):
                                opendeck.add_card()
                                you.rem_card()
                                selected_card = False
                                shift following cards left
                                redisplay cards
                                you.turn = False
                        if (new_card):
                            opendeck.add_card(new_card)
                            temp_hold_card_full = False
                            you.turn = False"""
                elif event.type == MOUSEBUTTONUP:
                    if (group_button.clicked_in()):
                        if (group_enabled):
                            group_enabled = False
                            cards_to_group.clear()
                            # grey out group button
                            group_button.update()
        else:
            # draw card from closedeck or opendeck
            done, throw_card = me.take_turn(closedeck, opendeck)
            if (done):
                # calculate points
                print("victory")
                # display hand
                # game over!
            else:
                # add throw_card to discard_deck
                user.turn = True

        # draw everything
        screen.blit(background, (0, 0))
        non_changing_sprites.draw(screen)
        changing_sprites.draw(screen)
        hand_sprite.draw(screen)
        pygame.display.flip()

    # game over
    pygame.quit()


if __name__ == "__main__":
    main()
