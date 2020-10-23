# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
import random
import math
import json
from openerp.exceptions import ValidationError


class player(models.Model):
     _name = 'res.partner'
     _inherit ='res.partner'
     _description ='Players inherit from res partner'

     is_player = fields.Boolean(default=False)
     fortresses = fields.One2many('game.fortress','player')
     fortressesk = fields.One2many(related='fortresses') # Per al kanban
     resources = fields.Many2many('game.resource', compute='_get_resources')
     raws = fields.One2many('game.raws','player', domain= lambda s: [('quantity','>',0)])
     characters = fields.Many2many('game.character', compute='_get_resources')
     unemployeds = fields.Many2many('game.character', compute='_get_resources')
     groups = fields.One2many('game.group','player')

     points = fields.Integer()
     points_history = fields.One2many('game.points','player')
     weapons_points = fields.Integer()  #Els punts a repartir en cada arma
     stuff_points = fields.Integer()    #Els punts a repartir en cada stuff
     food_points = fields.Integer()     #El nivell de tecnologia de menjar
     gold = fields.Float(default=100.0)
     max_fortresses = fields.Integer(default=1)

     clan = fields.Many2one('game.clan')
     clan_image = fields.Binary(related='clan.image_small')
     battles_as_attack = fields.Many2many('game.battle',relation='player_attacks', column1='p_a',column2='b_a')
     battles_as_defense = fields.Many2many('game.battle', relation='player_defends', column1='p_d',column2='b_d')

     stuff = fields.One2many('game.stuff','player')


     @api.depends('fortresses')
     def _get_resources(self):
         for player in self:
             player.resources = player.fortresses.mapped('resources')
             player.characters = player.fortresses.mapped('characters').filtered(lambda p: p.health > 0)
             player.unemployeds = player.fortresses.mapped('characters').filtered(lambda p: p.unemployed == True and p.health > 0)

     @api.model
     def create(self, values):
         new_id = super(player, self).create(values)
         print(values)
         new_id.reset_player()
         return new_id


     def reset_player(self):
         for p in self:
             p.weapons_points = 0
             p.stuff_points = 0
             for i in p.fortresses:
                 for c in i.resources:
                     c.unlink()
                 for c in i.characters:
                     c.unlink()
                 i.unlink()
             for i in p.stuff:
                 i.unlink()
             f_template = self.env.ref('game.fortress1')
             names = ["Ardglass","Abingdon","Swindlincote","Rotherham","Far Water","Todmorden","Walden","Lanercoast","Aempleforth","Barkamsted","Swindmore","Mountmend","Dalmellington","Blencogo","Beggar's Hole","Faversham","Lindow","Dungannon","Doveport","Peterbrugh","Limesvilles","Grimsby","Thralkeld","Dawsbury","Rotherhithe","Pavv","Holmfirth","Dalmellington","Eastcliff","Bleakburn"]
             f = self.env['game.fortress'].create({
                 'name': str(random.choice(names)),
                 'image': f_template.image,
                 'template': False,
                 #'level': 1,
                 'player': p.id
             })
             c_template = self.env.ref('game.cantera')
             c = self.env['game.resource'].create({
                 'name':'Cantera of: '+str(p.name),
                 'image': c_template.image,
                 'template': False,
                 'level' : 1,
                 'fortress': f.id,
                 'parent': c_template.id,
                 'knowledge': c_template.knowledge,
                 'produccions': [(6,0,c_template.produccions.ids)]
             })
             c_template = self.env.ref('game.barn')
             c = self.env['game.resource'].create({
                 'name': 'Barn of:'+str(p.name),
                 'image': c_template.image,
                 'template': False,
                 'level': 1,
                 'fortress': f.id,
                 'parent': c_template.id,
                 'knowledge': c_template.knowledge,
                 'produccions': [(6,0,c_template.produccions.ids)]
             })
             c_template = self.env.ref('game.kitchen')
             c = self.env['game.resource'].create({
                 'name': 'Kitchen of: '+str(p.name),
                 'image': c_template.image,
                 'template': False,
                 'level': 1,
                 'fortress': f.id,
                 'parent': c_template.id,
                 'knowledge': c_template.knowledge,
                 'produccions': [(6,0,c_template.produccions.ids)],
                 'production_spend': c_template.production_spend
             })
             for i in p.raws:
                 i.unlink()
             for i in self.env['game.raw'].search([]): # Assignar tots els Raws amb 0
                 r = self.env['game.raws'].create({'name': i.name, 'player': p.id, 'raw': i.id, 'quantity': 0})

             for i in range(0,10):  # Crear caracters
                 f.create_new_character()
             for i in range(0,100): # Crear Stuff
                 a = str(random.randint(0, 6))
                 s = self.env['game.stuff'].create({'type': str(a), 'player': p.id})
                 s.generate_name()
             p.assign_stuff()



     def update_resources(self):
         print('Updating resources')
         log = ' Updating resources '
         resources = self.env['game.resource'].search([('template', '=', False)]) # Busca els recursos que no son template
         for r in resources.filtered(lambda r: r.inactive == False ):
             if r.minutes_left > 0:
                 r.minutes_left = r.minutes_left - 1
             else:
                 # productions
                 log = log +" "+ r.produce()
                 # Les investigacions
                 log = log + " " + r.research()

         print('Updating characters')
         log = log + ' Updating characters '
         characters = self.env['game.character'].search([('health','>',0)])
         characters.grow()

         fortresses = self.env['game.fortress'].search([])
         log = log + fortresses.grow_population()

         print('Updating stuff')
         log = log + ' Updating stuff '
         stuff = self.env['game.stuff'].search([('minutes_left','>',0)])
         for s in stuff:
             s.write({'minutes_left': s.minutes_left - 1})

         print('Calculate wars')
         log = log + ' calculate wars '
         wars = self.env['game.battle'].search([('finished','=',False)]).filtered(lambda b: b.date <= fields.Datetime.now())
         for w in wars:
             w.compute_battle()

         self.search([]).calculate_points()

         self.env['game.log'].create({'title': 'Update' ,'description' : log})


     def create_new_fortress(self):
       for p in self:
         if p.max_fortresses > len(p.fortresses):
             f_template = self.env.ref('game.fortress1')
             names = ["Ardglass", "Abingdon", "Swindlincote", "Rotherham", "Far Water", "Todmorden", "Walden",
                      "Lanercoast", "Aempleforth", "Barkamsted", "Swindmore", "Mountmend", "Dalmellington", "Blencogo",
                      "Beggar's Hole", "Faversham", "Lindow", "Dungannon", "Doveport", "Peterbrugh", "Limesvilles",
                      "Grimsby", "Thralkeld", "Dawsbury", "Rotherhithe", "Pavv", "Holmfirth", "Dalmellington",
                      "Eastcliff", "Bleakburn"]
             f = self.env['game.fortress'].create({
                 'name': str(random.choice(names)),
                 'image': f_template.image,
                 'template': False,
                 'level': 1,
                 'player': p.id
             })

     def assign_stuff(self): # Assigna aleatoriament stuff als caracters
         for p in self:
             stuff = p.stuff.filtered(lambda s: len(s.character)==0)
             print(stuff)
             characters = p.characters.ids
             for s in stuff:
                 s.write({'character':random.choice(characters)})

     def calculate_points(self):
         for p in self:
             points = len(p.characters.filtered(lambda c: c.health > 0))
             points = points + len(p.stuff)
             points = points + sum(p.resources.mapped('level'))
             if p.points != points:
                 p.write({'points':points})
                 self.env['game.points'].create({'player': p.id, 'points': points})


################## FORTRESS ########################################################


class fortress(models.Model):
    _name = 'game.fortress'
    name = fields.Char()
    player = fields.Many2one('res.partner', ondelete='cascade')
    image = fields.Image(width=200)
    template = fields.Boolean()
    resources = fields.One2many('game.resource','fortress')
    available_resources = fields.Many2many('game.resource', compute='_get_available_resources')
    characters = fields.One2many('game.character','fortress')
    max_resources = fields.Integer(default=10)


    def create_new_character(self):
        for p in self:
            c_template = self.env.ref('game.character_template'+str(random.randint(1,3)))
            c_template2 = self.env.ref('game.character_template'+str(random.randint(1,12)))
            c = self.env['game.character'].create({
                'name': c_template2.name,
                'image': c_template.image,
                'fortress': p.id,
                'science': random.randint(1,20),
                'construction': random.randint(1,20),
                'mining': random.randint(1,20),
                'war': random.randint(1,20),
                'health': random.randint(1,20)
            })


    def _get_available_resources(self):
        for f in self:
            print('aaa')
            r = self.env['game.resource'].search([('template','=',True)])
            f.available_resources = [(6,0,r.ids)]

    def grow_population(self):
        log = ''
        for f in self:
            n_characters = len(f.characters)
            if n_characters > 1:  # Al menys necessitem una parelleta
                probability = n_characters / 10000  # Amb 100 caracters, hi ha un 1% de probabilitat de naixer uno nou
                log = log + "Probability to grow: " + str(probability)
                if probability > random.random():
                    c_template = self.env.ref('game.character_template' + str(random.randint(1, 2)))
                    c_template2 = self.env.ref('game.character_template' + str(random.randint(1, 12)))
                    c = self.env['game.character'].create({
                        'name': c_template2.name,
                        'image': c_template.image,
                        'fortress': f.id,
                        'science': random.randint(1, 20),
                        'construction': random.randint(1, 20),
                        'mining': random.randint(1, 20),
                        'war': random.randint(1, 20),
                        'health': random.randint(1, 20)
                    })
                    log = log + 'Growing population ' + probability + " " + str(c)
        print(log)
        return log


class resource(models.Model):
    _name = 'game.resource'
    name = fields.Char()
    produccions = fields.Many2many('game.raw')
    raws_stored = fields.One2many('game.raws_resource','resource')
    costs = fields.One2many('game.cost','resource')
    durations = fields.One2many('game.duration', 'resource')
    costs_child = fields.One2many(related='parent.costs')
    durations_child = fields.One2many(related='parent.durations')
    image = fields.Image(width=200)
    fortress = fields.Many2one('game.fortress', ondelete='cascade')

    level = fields.Integer()
    template = fields.Boolean()
    parent = fields.Many2one('game.resource', domain="[('template', '=', True)]")
    minutes_left = fields.Integer()
    const_percent = fields.Float()#compute='_get_const_percent') # sera computed el % de contruccio
    # En cas de ser barracks o academy o laboratory
    knowledge = fields.Selection([('0','None'),('1','Militar'),('2','Scientific'),('3','Mining'),('4','Construction'),('5','All Skills')])
    characters = fields.One2many('game.character','resource')
    researches = fields.One2many('game.research','resource',readonly=True)
    inactive = fields.Boolean(default=False)
    current_productionsk = fields.Char(compute='_get_productions')
    characters_productions = fields.Float(compute='_get_productions')
    color = fields.Integer(compute='_get_color')
    # El resource pot ser a medida. L'usuari el crea definint el que consumeix i el que produeix
    custom_production = fields.Many2one('game.raw')
    production_spend = fields.Selection([('0','Nothing'),('1','Construccio'),
                                        ('2','Armes Blanques'),('3','Armes Foc'),
                                        ('4','Nutricio'),('5','Tecnologia'),
                                        ('6','Medicina'),('7','Energia')], default='0')

    def _get_color(self):
        for i in self:
            if i.template:
                i.color = 4
            else:
                i.color = 3
            if i.inactive:
                i.color = 1


    @api.depends('minutes_left')
    def _get_const_percent(self):
        for r in self:
            total_time = r.durations_child.filtered(lambda s: s.level == r.level).minutes
            if total_time > 0:
                r.const_percent = 100- (r.minutes_left / total_time)*100

    def build_it(self):
        for r in self:
            fortress = self.env['game.fortress'].browse(self.env.context['fortress'])
            if fortress.max_resources > len(fortress.resources):
                 r.create({'name': r.name, 'image': r.image, 'fortress': self.env.context['fortress'],
                      'level': 1, 'template': False, 'parent': r.id,
                      'minutes_left': r.durations.filtered(lambda s: s.level == 1).minutes,
                      'knowledge': r.knowledge,
                      'produccions': [(6, 0, r.produccions.ids)],
                      'production_spend': r.production_spend
                      })

    def assign_to_resource(self):
        for r in self:
            character = self.env['game.character'].browse(self.env.context['character'])
            character.write({'resource': r.id})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }



    def _get_productions(self):
        for r in self:
            r.current_productionsk = " " # r.produccions.mapped(lambda p: str(p.name)+" "+str((r.level*1440)/p.production_cost))
            characters_increment = 0
            if r.characters:
                characters_p = sum(cc.mining for cc in r.characters) + 1
                characters_increment = math.log(characters_p, 1.05)  # Augment logaritmic
            r.characters_productions = characters_increment


    def produce(self):
        log = 'produce: '
        for r in self:
            # Produccions i gastos en les produccions
            productions = r.produccions
            c_productions = r.characters_productions
            for p in productions:  # La llista de les produccions d'aquest recurs
                raws = r.fortress.player.raws.filtered(lambda r: r.raw.id == p.id)  # El raws del player que es d'aquesta produccio
                for i in raws:
                    q = (1440 * r.level) / p.production_cost # Costa més quan millor és el material
                    log = log +" "+ str(p.name) + " Res Production:   " + str(q)
                    # ara cal calcular la produccio dels characters:
                    q = q + (c_productions / p.production_cost)  # Costa més quan millor és el material
                    log = log +" "+ str(p.name) + " Total production: " + str(q)+" Cost: "+str(p.production_cost)
                    if r.production_spend != '0':
                        p_spend = r.production_spend
                        raws_needed = {'0':0,'1': i.raw.construccio, '2': i.raw.armesblanques, '3': i.raw.armesfoc,
                                       '4': i.raw.nutricio, '5': i.raw.tecnologia, '6':i.raw.medicina, '7': i.raw.energia}
                        raws_needed = raws_needed[p_spend] * i.raw.production_cost * q
                        log = log +" "+ 'Raws needed: '+str(p_spend)+" "+ str(raws_needed)
                        r._spend(raws_needed)

                    i.write({'quantity': q + i.quantity})
            # Els consums en cas de que no produisca res
            if (len(productions) == 0 and r.production_spend != '0'):
                raws_needed = 2**r.level * (len(r.characters)+1)  # El consum depen del nivell i dels ocupants
                log = log +" "+  'Non productive raws needed: '+str(raws_needed)
                r._spend(raws_needed)
        return log

    def research(self):
        log = ''
        for r in self:
            #print(r.researches)
            for research in r.researches.filtered(lambda s: s.minutes_left > 0):
                research.write({'minutes_left': research.minutes_left - 1})
                log = log + 'Updating researches'
                log = log + research.do_research()
        return log


    def _spend(self,raws_needed):
        for r in self:
            raws_stored = r.raws_stored
            p_spend = r.production_spend
            for ra in raws_stored:
                r_properties = {'0': 0, '1': ra.raw.construccio, '2': ra.raw.armesblanques,
                                '3': ra.raw.armesfoc,
                                '4': ra.raw.nutricio+(r.fortress.player.food_points**2), # Els punts de nutrició del player fan que siga més eficient el RAW
                                '5': ra.raw.tecnologia, '6': ra.raw.medicina,
                                '7': ra.raw.energia}
                print("Propietats del RAW: "+str(r_properties))
                raw_potential = 1.1 ** r_properties[p_spend]

                raw_spend = raws_needed / raw_potential
                print(str(raw_potential) + " Raw Spend: " + str(raw_spend))
                if raw_spend < ra.quantity:
                    ra.write({'quantity': ra.quantity - raw_spend})
                    raws_needed = 0
                else:
                    ra.write({'quantity': 0})
                    raws_needed = raws_needed - raw_potential * ra.quantity
            print(raws_needed)
            if raws_needed > 0:
                r.write({'inactive': True})

    def level_up(self):
        for r in self:
            if r.minutes_left == 0:
                level = r.level + 1
                minutes_left = r.durations_child.filtered(lambda d: d.level == level)
                if minutes_left:
                  minutes_left = minutes_left[0].minutes
                  r.write({'level': level, 'minutes_left': minutes_left})

    def new_research(self):
        for r in self:
            type = self.env.context['type']
            self.env['game.research'].create({
                'resource': r.id,
                'type': type,
                'minutes_left': 1440/r.level
            })


    @api.constrains('researches')
    def _check_researches(self):
        for r in self:
            if len(r.researches) > 0 and r.knowledge != '2':
                raise ValidationError("Your cannot research in this resource")

class cost(models.Model):
    _name = 'game.cost'
    name = fields.Char()
    resource = fields.Many2one('game.resource') # Que recurs
    level = fields.Integer() # Cal indicar el que consumeix en cada nivell
    raw = fields.Many2one('game.raw') # Que material
    cost = fields.Float()  #cost total

class duration(models.Model):
    _name = 'game.duration'
    name = fields.Char()
    resource = fields.Many2one('game.resource') # Que recurs
    level = fields.Integer() # Cal indicar el que tarda en cada nivell
    minutes = fields.Integer()  #cost total
    max_characters = fields.Integer()

class raw(models.Model):
    _name = 'game.raw'
    name = fields.Char()
    image = fields.Image(width=200)
    public_hash = fields.Char(readonly=True)
    hidden_hash = fields.Char(readonly=True) # El hash és com la composició atòmica, que no es sap inicialment.
    # Propietats dels materials:
    construccio = fields.Float()
    armesblanques = fields.Float()
    armesfoc = fields.Float()
    nutricio = fields.Float()
    tecnologia = fields.Float()
    medicina = fields.Float()
    energia = fields.Float()
    production_cost = fields.Float(compute="_get_production_cost") # Cada raw te un cost de producció en funció de les propietats


    def _get_production_cost(self):
        for r in self:
            propietats = [1.1**r.construccio, 1.1**r.armesblanques, 1.1**r.armesfoc, 1.1**r.nutricio, 1.1**r.tecnologia, 1.1**r.medicina, 1.1**r.energia]
            r.production_cost = sum(propietats)
            # print(r.production_cost)


class raws(models.Model):
    _name = 'game.raws'
    name = fields.Char(related='raw.name')
    player = fields.Many2one('res.partner', ondelete='cascade')
    clan = fields.Many2one('game.clan', ondelete='cascade')
    raw = fields.Many2one('game.raw')
    quantity = fields.Float(digits = (12,5))
    production = fields.Float(compute='get_production')
    total_production = fields.Float(compute='get_production')
    character_production = fields.Float(compute='get_production')
    production_cost = fields.Float(related='raw.production_cost')

    def get_production(self):
        for raws in self:
            resources = raws.player.fortresses.mapped('resources').filtered(lambda r: r.minutes_left == 0 and r.inactive == False)
            production = 0
            c_production = 0

            for resource in resources:
                if raws.raw.id in resource.produccions.ids:
                    production = production + ((1440 * resource.level) / raws.raw.production_cost)
                    c_production = c_production + ( resource.characters_productions / raws.raw.production_cost )
                    #print(raws.raw.name+" "+resource.name)


            raws.production = production
            raws.character_production = c_production
            raws.total_production = production + c_production

    @api.constrains('player','clan')
    def _check_owner(self):
        for r in self:
            if len(r.player) > 0  and len(r.clan) > 0:
                raise ValidationError("A raw cannot of a player and a clan at the same time")




class raws_resource(models.Model):
    _name = 'game.raws_resource'
    name = fields.Char(related='raw.name')
    resource = fields.Many2one('game.resource', ondelete='cascade')
    raw = fields.Many2one('game.raw')
    quantity = fields.Float(digits = (12,5))
    player = fields.Many2one(related='resource.fortress.player')


# Un recurs és, per exemple, una mina, que consumeix electricitat i produeix varis materials a un ritme distint
# Cada recurs té una llista de production que indica qué i quant produeix o consumeix.
# Els materials inicials tenen unes propietats basiques, hi ha milers de materials primaris per descobrir i
# amés es poden mesclar entre ells per tindre altres propietats.
# Un jugador pot descobrir un material i publicar el seu hash o no. Pot anar provant hashes (tarda un temps) o
# invertir en educacio i investigacio i ser mes probable que el trobe.
# La gracia esta en que els jugadors creen una base de dades del que van descobrint i que siga o no pública.

class character(models.Model):
    _name = 'game.character'
    name = fields.Char()
    image = fields.Image(width=200)
    fortress = fields.Many2one('game.fortress', ondelete='cascade')
    player = fields.Many2one(related='fortress.player')
    science = fields.Float()
    construction = fields.Float()
    mining = fields.Float()
    war = fields.Float()
    health = fields.Float()
    age = fields.Integer(default=1)
    resource = fields.Many2one('game.resource') # Falta que no puga ser d'un altre fortress
    stuff = fields.One2many('game.stuff','character')
    unemployed = fields.Boolean(compute = '_get_unemployed')
    resources_available = fields.One2many(related='fortress.resources', string='Resources available')

    def grow(self):
        for c in self:
            age = c.age + 1
            health = c.health
            # a partir de 100 anys, quasi segur que moren
            # 100 anys son 36500 dies, cada dia un minut de joc
            # un caracter dura com a molt 25 dies de joc
            # Funcio doble exponencial per a que dure menys de 25 dies
            p_mort = (1.00000000000001 ** (age ** 3.2) - 1) / 100
            # print(p_mort)
            if random.random() < p_mort:
                health = 0
                print('MORT!' + str(c.name))
            elif health < 100:
                health = health + 1
            c.write({'health': health, 'age': age})
            if c.resource:
                if not c.resource.inactive:
                    level = c.resource.level
                    k = c.resource.knowledge
                    if k == '1':  # Barracks
                        war = c.war + level
                        c.write({'war': war})
                    elif k == '2':  # Laboratory
                        science = c.science + level
                        c.write({'science': science})
                    elif k == '3':  # Mining
                        mining = c.mining + level
                        c.write({'mining': mining})
                    elif k == '4':
                        construction = c.construction + level
                        c.write({'construction': construction})
                    elif k == '5':
                        construction = c.construction + level
                        mining = c.mining + level
                        c.write({'construction': construction, 'mining': mining})

    def _get_unemployed(self):
        for c in self:
            if len(c.resource) == 0:
                c.unemployed = True
            else:
                c.unemployed = False

    @api.onchange('resource')
    def set_fortress(self):
        self.fortress = self.resource.fortress.id

    @api.onchange('name')
    def set_image(self):
        c_template = self.env.ref('game.character_template' + str(random.randint(1, 3)))
        self.image = c_template.image

    guns = fields.Many2many('game.stuff', compute='_get_stuff_type')
    armors =  fields.Many2many('game.stuff', compute='_get_stuff_type')
    melees = fields.Many2many('game.stuff', compute='_get_stuff_type')

    gun_power = fields.Integer(compute='_get_stuff_type')
    melee_power = fields.Integer(compute='_get_stuff_type')
    armor_power = fields.Integer(compute='_get_stuff_type')


    def _get_stuff_type(self):
        for c in self:
            c.guns = c.stuff.filtered(lambda s: s.type=='0')
            c.armors = c.stuff.filtered(lambda s: s.type == '2')
            c.melees = c.stuff.filtered(lambda s: s.type == '1')

            best = c.stuff.filtered(lambda s: s.type == '0') # Si va equipat en armes de foc
            if best:
                best = best.sorted(key=lambda s: s.shoot, reverse=True)[0].shoot # La millor arma de foc
            else:
                best = 0
            c.gun_power = best

            best = c.stuff.filtered(lambda s: s.type == '1') # Si va equipat en armes de melee
            if best:
                best = best.sorted(key=lambda s: s.melee, reverse=True)[0].melee # La millor arma de melee
            else:
                best = 0
            c.melee_power = best

            best = c.stuff.filtered(lambda s: s.type == '2') # Si va equipat en armadura
            if best:
                best = best.sorted(key=lambda s: s.armor, reverse=True)[0].armor # La millor arma de foc
            else:
                best = 0
            c.armor_power = best


    def action_resurrect(self):
        print('RESUREECCCCCTTTT')
        for c in self.browse(self.env.context.get('active_ids')):
            #print(c.health)
            c.write({'health':100})

    # Provar el records.

class character_template(models.Model):
    _name = 'game.character.template'
    image = fields.Image(width=200)
    name = fields.Char()

### Les investigacions

class research(models.Model):
    _name = 'game.research'
    name = fields.Char()
    resource = fields.Many2one('game.resource', ondelete='cascade')
    type = fields.Selection([('1','Weapons'),('2','Chemist'),('3','Nutrition'),('4','Medicine'),('5','Energy')])
    minutes_left = fields.Integer()
    research_percent = fields.Float(compute='get_percent') # sera computed el % de investigació
    result = fields.Char()

    @api.depends('minutes_left')
    def get_percent(self):
        for r in self:
            total_time = 1440/r.resource.level
            #print(total_time)
            if total_time > 0:
                r.research_percent = 100 - (r.minutes_left / total_time) * 100


    def do_research(self):
        log = 'do research'
        for r in self.filtered(lambda s: s.minutes_left == 1):
            if r.type == '1':
                log = log + 'millora en armes'
                character_skills = sum(r.resource.characters.mapped('science'))
                weapons_points = r.resource.fortress.player.weapons_points
                ratio_skills_points = math.ceil(character_skills/(weapons_points+1))+1
                points_extra = random.randint(0,ratio_skills_points)
                r.resource.fortress.player.write({'weapons_points': weapons_points + points_extra})
                r.write({'result': str(points_extra)+' Points extra in Weapon Points \n Ratio Skills/Weapon points: '+str(ratio_skills_points)})
            if r.type == '2':
                log = log + 'millora en química'
                character_skills = sum(r.resource.characters.mapped('science'))
                n_raws = len(r.resource.fortress.player.raws)
                ratio_skills_n_raws = math.ceil(character_skills/(n_raws+1))+1
                # print(ratio_skills_n_raws)
                chance = random.randint(0, ratio_skills_n_raws)
                # print(str(n_raws)+' '+str(chance))
                if chance >= random.randint(0,1):
                   not_discovered = self.env['game.raw'].search([]) - r.resource.fortress.player.raws.mapped('raw')
                   not_discovered = not_discovered.ids
                   random.shuffle(not_discovered)
                   # print(not_discovered)
                   new_raw = not_discovered[0]
                   self.env['game.raws'].create({'player': r.resource.fortress.player.id, 'raw': new_raw})
                   r.write({'result': 'Discovered new Raw material: '+str(self.env['game.raw'].search([('id','=',new_raw)]).name)})
                   log = log + 'Discovered: '+ str(new_raw)
            if r.type == '3':
                log = log + 'millora en nutricio'
                character_skills = sum(r.resource.characters.mapped('science'))
                food_points = r.resource.fortress.player.weapons_points
                ratio_skills_points = math.ceil(character_skills/(food_points+1))+1
                points_extra = random.randint(0,ratio_skills_points)
                r.resource.fortress.player.write({'food_points': food_points + points_extra})
                r.write({'result': str(points_extra)+' Points extra in Food Points \n Ratio Skills/Food points: '+str(ratio_skills_points)})
            if r.type == '4':
                log = log + 'millora en medicina'
            if r.type == '5':
                log = log + 'millora en energia'
            log = log + r.result
        return log


        ### Els accessoris

## Cal crear un wizard per a crear stuff.

class stuff(models.Model):
    _name = 'game.stuff'
    name = fields.Char(readonly=True)
    hash = fields.Char(readonly=True)
    image = fields.Image(width=100,readonly=True)
    character = fields.Many2one('game.character')
    player = fields.Many2one('res.partner')
    type = fields.Selection([('0','Fire Weapons'),('1','Melee Weapons'),('2','Armor'),
                             ('3','Chemist'),('4','Nutrition'),('5','Medicine'),('6','Energy')], required=True)
    # Propietats:
    melee = fields.Integer()
    shoot = fields.Integer()
    armor = fields.Integer()

    science = fields.Integer()
    cook = fields.Integer()
    medicine = fields.Integer()
    energy = fields.Integer()

    minutes_left = fields.Integer()
    duration = fields.Integer()

    def generate_name(self):
        for s in self:
         words = {'1': ["Sword","Knive","Dagger","Axe","Sickle","Kama","Halberd","Spear","Guandao",
                 "scythe","Mace","Stick","Nunchaku"],
                 '0': ["Gun","Shotgun","Rifle","Carbine","Machine Gun","Sniper rifle","Musket"],
                 '2': ["Armor", "Uniform", "Camouflaje armor", "Bulletproof vest"],
                 '3': ["Microscope", "Tube", "Pipette", "Balance", "Beaker", "Crucible"],
                 '4': ["Knive","Balance","Stove","Oven","Pan","Pot"],
                 '5': ["Thermometer", "Cannula", "Enema", "Scissors", "Stethoscope", "Bandage"],
                 '6': ["Cables", "Voltimeter", "Generator", "Solar Panel", "Boiler", "Engine"]}

         adjectives = ["Premium","Obsolete","Glorious","False","Astonishing",
                          "Splendid", "Pathetic", "Bizarre", "Sordid", "Studendous", "Sharp",
                          "Overconfident", "Pleasant", "Sweet", "Last", "Curly", "Freezing", "Aberrant",
                          "Profuse", "Dangerous", "Powerful"]

         word = words[s.type]
         random.shuffle(word)
         word = word[0]
         random.shuffle(adjectives)
         adjective = adjectives[0]
         image = self.env.ref('game.stuff_template'+str(s.type)).image
         s.write({'name': adjective+" "+word,'image':image})
         s.generate_properties()


    def generate_properties(self):
        for s in self:
            points = 0
            if s.player:
                if s.type == '0' or s.type == '1':
                    points = s.player.weapons_points
                else:
                    points = s.player.stuff_points
            points = points + 100
            base_points = {'0': 0, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0}
            p = round(points * random.betavariate(4,1)+1) # Betavariate en aquests parametres dona normalment numeros grans
            base_points[s.type] = p
            points = points - p
            while points > 0:
                p = round(points * random.random()+1)
                a = str(random.randint(0,6))
                base_points[a] = base_points[a]+p
                points = points - p
                print(points)
            s.write({'melee':base_points['1'], 'shoot':base_points['0'],'armor': base_points['2'],
                     'science': base_points['3'],'cook': base_points['4'],'medicine': base_points['5'],'energy': base_points['6']})



    @api.onchange('character')
    def _onchange_character(self):
        self.player = self.character.fortress.player.id

    def take_away(self):
        for s in self:
            s.write({'character':False})


class stuff_images(models.Model):
    _name = 'game.stuff.image'
    type = fields.Selection([('0','Fire Weapons'),('1','Melee Weapons'),('2','Armor'),
                             ('3','Chemist'),('4','Nutrition'),('5','Medicine'),('6','Energy')])
    image = fields.Image(width=200)

class log(models.Model):
    _name = 'game.log'
    name = fields.Datetime(default=lambda self: fields.Datetime.now())
    title = fields.Char()
    description = fields.Text()

class points(models.Model):
    _name = 'game.points'
    player = fields.Many2one('res.partner')
    date = fields.Char(default=lambda self: fields.Datetime.now())
    points = fields.Integer()


class group(models.Model):
    _name = 'game.group'
    _inherits = {'game.character':'character_id'}
   # name = fields.Char()
    #player = fields.Many2one('res.partner', domain="[('is_player','=',True)]")
    leader = fields.Many2one('game.character', domain="[('player','=',player)]")
    members = fields.Many2many('game.character', domain="[('player','=',player)]")
    subgroups = fields.Many2many('game.group',
                              relation='super_group',
                              column1='super_id',
                              column2='sub_id',
                              domain="[('player','=',player.id)]")


    @api.constrains('player','leader','characters','groups')
    def _check_constrains(self):
        for g in self:
            player = g.player.id
            if g.leader.player.id != player:
                raise ValidationError("The leader is not a valid character")
            if len(self.search([('leader','=',g.leader.id)])) > 1:
                raise ValidationError("The leader is a leader for other group")
            if len(g.characters.mapped('player')) > 1:
                raise ValidationError("All the characters have to be of the same player")
            elif g.characters.mapped('player')[0].id != player:
                raise ValidationError("The characters have to be of the same player")



