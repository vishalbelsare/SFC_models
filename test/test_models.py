from unittest import TestCase

from sfc_models.models import *
from sfc_models.sectors import Household, DoNothingGovernment


def kill_spaces(s):
    """
    remove spaces from a string; makes testing easier as white space conventions may change in equations
    :param s:
    :return:
    """
    s = s.replace(' ', '')
    return s

class TestEntity(TestCase):
    def test_ctor(self):
        Entity.ID = 0
        a = Entity()
        self.assertEqual(a.ID, 0)
        b = Entity(a)
        self.assertEqual(b.ID, 1)
        self.assertEqual(b.Parent.ID, 0)

    def test_root(self):
        a = Entity()
        b = Entity(a)
        c = Entity(b)
        self.assertEqual(a, a.GetModel())
        self.assertEqual(a, b.GetModel())
        self.assertEqual(a, c.GetModel())


class Stub(object):
    """
    Use the stub_fun to count how many times a method has been called.
    Used for testing the iteration in the Model class; the output depends upon the sector,
    which are tested separately.
    """

    def __init__(self):
        self.Count = 0

    def stub_fun(self):
        self.Count += 1

    def stub_return(self):
        self.Count += 1
        return [(str(self.Count), 'a', 'b')]


class TestModel(TestCase):
    def test_GenerateFullCodes_1(self):
        mod = Model()
        country = Country(mod, 'USA!', 'US')
        household = Sector(country, 'Household', 'HH')
        mod.GenerateFullSectorCodes()
        self.assertEqual(household.FullCode, 'HH')

    def test_GenerateFullCodes_2(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        can = Country(mod, 'Canada', 'Eh?')
        household = Sector(us, 'Household', 'HH')
        can_hh = Sector(can, 'Household', 'HH')
        mod.GenerateFullSectorCodes()
        self.assertEqual(household.FullCode, 'US_HH')
        self.assertEqual(can_hh.FullCode, 'Eh?_HH')

    def test_LookupSector(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        can = Country(mod, 'Canada', 'Eh?')
        household = Sector(us, 'Household', 'HH')
        can_hh = Sector(can, 'Household', 'HH')
        mod.GenerateFullSectorCodes()
        self.assertEqual(household, mod.LookupSector('US_HH'))
        self.assertEqual(can_hh, mod.LookupSector('Eh?_HH'))
        with self.assertRaises(KeyError):
            mod.LookupSector('HH')

    def test_AddExogenous(self):
        mod = Model()
        # Does not validate that the sector exists (until we call ProcessExogenous)
        mod.AddExogenous('code','varname', 'val')
        self.assertEqual([('code', 'varname', 'val')], mod.Exogenous)

    def test_AddExogenous_list(self):
        mod = Model()
        # Does not validate that the sector exists (until we call ProcessExogenous)
        val = [0, 1, 2]
        mod.AddExogenous('code', 'varname', val)
        self.assertEqual([('code', 'varname', repr(val))], mod.Exogenous)

    def test_AddExogenous_tuple(self):
        mod = Model()
        val = (0, 1, 2)
        mod.AddExogenous('code', 'varname', val)
        self.assertEqual([('code', 'varname', repr(val))], mod.Exogenous)

    def test_AddInitialCondition(self):
        mod = Model()
        # Does not validate that the sector exists until processing
        mod.AddInitialCondition('code', 'varname', 0.1)
        self.assertEqual([('code', 'varname', str(0.1))], mod.InitialConditions)
        with self.assertRaises(ValueError):
            mod.AddInitialCondition('code2','varname2', 'kablooie!')

    def test_GenerateInitialCond(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        household = Sector(us, 'Household', 'HH')
        mod.GenerateFullSectorCodes()
        mod.InitialConditions = [('HH', 'F', '0.1')]
        out = mod.GenerateInitialConditions()
        self.assertEqual([('HH_F(0)', '0.1', 'Initial Condition')], out)

    def test_GenerateInitialCondFail(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        household = Sector(us, 'Household', 'HH')
        mod.GenerateFullSectorCodes()
        mod.InitialConditions = [('HH', 'FooFoo', '0.1')]
        with self.assertRaises(KeyError):
            out = mod.GenerateInitialConditions()

    def test_ProcessExogenous(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        household = Sector(us, 'Household', 'HH')
        mod.GenerateFullSectorCodes()
        mod.Exogenous = [('HH', 'F', 'TEST')]
        mod.ProcessExogenous()
        self.assertEqual('EXOGENOUS TEST', household.Equations['F'])

    def test_GetSectors(self):
        mod = Model()
        self.assertEqual(0, len(mod.GetSectors()))
        us = Country(mod, 'USA', 'US')
        self.assertEqual(0, len(mod.GetSectors()))
        household = Sector(us, 'Household', 'HH')
        self.assertEqual(1, len(mod.GetSectors()))
        hh2 = Sector(us, 'Household2', 'HH2')
        self.assertEqual(2, len(mod.GetSectors()))
        ca = Country(mod, 'country', 'code')
        hh3 = Sector(ca, 'sec3', 'sec3')
        secs = mod.GetSectors()
        self.assertEqual(3, len(secs))
        self.assertIn(household, secs)
        self.assertIn(hh2, secs)
        self.assertIn(hh3, secs)

    def test_Fixaliases(self):
        mod = Model()
        c = Country(mod, 'co', 'co')
        sec1 = Sector(c, 'sec1', 'sec1')
        sec1.AddVariable('x', 'eqn x', '')
        varname = sec1.GetVariableName('x')
        ID = "{0}".format(sec1.ID)
        self.assertIn(ID, varname)
        sec2 = Sector(c, 'sec2', 'sec2')
        sec2.AddVariable('two_x', 'Test variable', '2 * {0}'.format(varname))
        self.assertEqual('2*'+varname, kill_spaces(sec2.Equations['two_x']))
        mod.GenerateFullSectorCodes()
        mod.FixAliases()
        self.assertEqual('2*sec1_x', kill_spaces(sec2.Equations['two_x']))

    def test_fix_aliases_2(self):
        mod = Model()
        c = Country(mod, 'co', 'co')
        sec1 = Sector(c, 'sec1', 'sec1')
        sec1.AddVariable('x', 'eqn x', '')
        varname = sec1.GetVariableName('x')
        # The ID is the key part of the alias
        self.assertIn('{0}'.format(sec1.ID), varname)
        sec2 = Sector(c, 'sec2', 'sec2')
        mod.RegisterCashFlow(sec1, sec2, 'x')
        mod.GenerateRegisteredCashFlows()
        self.assertEqual('-'+varname, sec1.CashFlows[0])
        self.assertEqual('+' + varname, sec2.CashFlows[0])
        mod.GenerateFullSectorCodes()
        mod.FixAliases()
        self.assertEqual('-sec1_x', kill_spaces(sec1.CashFlows[0]))
        self.assertEqual('+sec1_x' , kill_spaces(sec2.CashFlows[0]))

    def test_ForceExogenous2(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        household = Sector(us, 'Household', 'HH')
        mod.GenerateFullSectorCodes()
        mod.Exogenous = [('HH', 'Foo', 'TEST')]
        with self.assertRaises(KeyError):
            mod.ProcessExogenous()

    def test_GenerateEquations(self):
        # Just count the number if times the stub is called
        stub = Stub()
        mod = Model()
        us = Country(mod, 'USA', 'US')
        h1 = Sector(us, 'Household', 'HH')
        h2 = Sector(us, 'Capitalists', 'CAP')
        h1.GenerateEquations = stub.stub_fun
        h2.GenerateEquations = stub.stub_fun
        mod.GenerateEquations()
        self.assertEqual(2, stub.Count)

    def test_GenerateIncomeEquations(self):
        stub = Stub()
        mod = Model()
        us = Country(mod, 'USA', 'US')
        h1 = Sector(us, 'Household', 'HH')
        h1.GenerateIncomeEquations = stub.stub_fun
        mod.GenerateIncomeEquations()
        self.assertEqual(1, stub.Count)

    def test_CreateFinalFunctions(self):
        stub = Stub()
        mod = Model()
        us = Country(mod, 'USA', 'US')
        h1 = Sector(us, 'Household', 'HH')
        h2 = Sector(us, 'Household2', 'H2')
        h1.CreateFinalEquations = stub.stub_return
        h2.CreateFinalEquations = stub.stub_return
        out = mod.CreateFinalEquations()
        out = out.split('\n')
        self.assertTrue('1' in out[0])
        self.assertTrue('2' in out[1])

    def test_FinalEquationFormating(self):
        eq = [('x', 'y + 1', 'comment_x'),
              ('y', 'EXOGENOUS 20', 'comment_y'),
              ('z', 'd', 'comment_z')]
        mod = Model()
        out = mod.FinalEquationFormatting(eq)
        # Remove spaces; what matters is the content
        out = out.replace(' ', '').split('\n')
        target = ['x=y+1#comment_x', 'z=d#comment_z', '', '#ExogenousVariables', '', 'y=20#comment_y',
                  '', 'MaxTime=100','Err_Tolerance=0.001']
        self.assertEqual(target, out)

    def test_dumpequations(self):
        # Since dump format will change, keep this as a very loose test. We can tighten the testing
        # on Sector.Dump() later
        mod = Model()
        country = Country(mod, 'USA! USA!', 'US')
        household = Sector(country, 'Household', 'HH')
        hh_dump = household.Dump()
        mod_dump = mod.DumpEquations()
        self.assertEqual(hh_dump, mod_dump)

    def test_GetTimeSeries(self):
        mod = Model()
        mod.TimeSeriesCutoff = None
        mod.EquationSolver.TimeSeries = {'t': [0, 1, 2]}
        with self.assertRaises(KeyError):
            mod.GetTimeSeries('q')
        with self.assertRaises(KeyError):
            mod.GetTimeSeries('q', cutoff=1)
        self.assertEqual([0, 1, 2], mod.GetTimeSeries('t'))
        self.assertEqual([0, 1], mod.GetTimeSeries('t', cutoff=1))
        mod.TimeSeriesCutoff = 1
        self.assertEqual([0, 1], mod.GetTimeSeries('t'))
        # Passed parameter overrides default .GetTimeSeries member.
        self.assertEqual([0,], mod.GetTimeSeries('t', cutoff=0))

    def test_GetTimeSeriesPop(self):
        mod = Model()
        mod.EquationSolver.TimeSeries = {'t': [0,1,2]}
        mod.TimeSeriesSupressTimeZero = True
        self.assertEqual([1, 2], mod.GetTimeSeries('t'))



class TestSector(TestCase):
    def test_ctor_chain(self):
        mod = Model()
        country = Country(mod, 'USA! USA!', 'US')
        household = Sector(country, 'Household', 'HH')
        self.assertEqual(household.Parent.Code, 'US')
        self.assertEqual(household.Parent.Parent.Code, '')

    def test_HasNoF(self):
        mod = Model()
        country = Country(mod, 'name', 'code')
        sec = Sector(country, 'Name', 'Code', has_F=False)
        sec.GenerateIncomeEquations()
        self.assertNotIn('F', sec.GetVariables())

    def test_GetVariables(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        can_hh = Sector(can, 'Household', 'HH')
        can_hh.AddVariable('y', 'Vertical axis', '2.0')
        can_hh.AddVariable('x', 'Horizontal axis', 'y - t')
        self.assertEqual(can_hh.GetVariables(), ['F', 'LAG_F', 'x', 'y'])

    def test_GetVariableName_1(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        household = Household(us, 'Household', 'HH', .9, .2)
        mod.GenerateFullSectorCodes()
        household.GenerateEquations()
        self.assertEqual(household.GetVariableName('AlphaFin'), 'HH_AlphaFin')

    def test_GetVariableName_2(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        household = Household(us, 'Household', 'HH', .9, .2)
        ID = household.ID
        target = '_{0}_{1}'.format(ID, 'AlphaFin')
        self.assertEqual(target, household.GetVariableName('AlphaFin'))


    def test_GetVariableName_3(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        hh = Sector(us, 'Household', 'HH')
        mod.GenerateFullSectorCodes()
        with self.assertRaises(KeyError):
            hh.GetVariableName('Kaboom')

    def test_AddCashFlow(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        s.AddCashFlow('A', 'H_A', 'Desc A')
        s.AddCashFlow('- B', 'H_B', 'Desc B')
        s.AddCashFlow(' - C', 'H_C', 'Desc C')
        self.assertEqual(['+A', '-B', '-C'], s.CashFlows)

    def test_AddCashFlow_2(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        s.AddCashFlow('A', 'equation', 'Desc A')
        s.AddCashFlow('', 'equation', 'desc')
        with self.assertRaises(ValueError):
            s.AddCashFlow('-', 'B', 'Desc B')
        with self.assertRaises(ValueError):
            s.AddCashFlow('+', 'X', 'Desc C')
        self.assertEqual(['+A'], s.CashFlows)
        self.assertEqual('equation', s.Equations['A'])

    def test_AddCashFlow_3(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        s.AddVariable('X', 'desc', '')
        s.AddCashFlow('X', 'equation', 'Desc A')
        self.assertEqual('equation', s.Equations['X'])

    def test_GenerateIncomeEquations(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        s.GenerateIncomeEquations()
        self.assertEqual('', s.Equations['F'])
        self.assertEqual('', s.Equations['LAG_F'])

    def test_GenerateIncomeEquations_2(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        s.CashFlows.append('X')
        s.GenerateIncomeEquations()
        self.assertEqual('LAG_F+X', s.Equations['F'])
        self.assertEqual('F(k-1)', s.Equations['LAG_F'])

    def test_GenerateIncomeEquations_3(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        s.CashFlows.append('X')
        s.CashFlows.append('Y')
        s.GenerateIncomeEquations()
        self.assertEqual('LAG_F+X+Y', s.Equations['F'])
        self.assertEqual('F(k-1)', s.Equations['LAG_F'])

    def test_GenerateFinalEquations(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        mod.GenerateFullSectorCodes()
        s.Equations = {'F': '', 'X': 't+1', 'Y': 'X+1'}
        s.VariableDescription = {'F': 'DESC F', 'X': 'DESC X', 'Y': 'DESC Y'}
        out = s.CreateFinalEquations()
        # Since F has an empty equation, does not appear.
        targ = [('HH_X', 't+1', '[X] DESC X'), ('HH_Y', 'HH_X+1', '[Y] DESC Y')]
        # Kill spacing in equations
        out = [(x[0], x[1].replace(' ', ''), x[2]) for x in out]
        self.assertEqual(targ, out)

    def test_GenerateAssetWeightings_1(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        s.GenerateAssetWeighting((), 'MON')
        self.assertEqual('1.0', s.Equations['WGT_MON'])
        self.assertEqual('F*WGT_MON', kill_spaces(s.Equations['DEM_MON']))

    def test_GenerateAssetWeightings_2(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        s.GenerateAssetWeighting([('BOND', '0.5'),], 'MON')
        self.assertEqual('0.5', s.Equations['WGT_BOND'])
        self.assertEqual('F*WGT_BOND', kill_spaces(s.Equations['DEM_BOND']))
        self.assertEqual('1.0-WGT_BOND', kill_spaces(s.Equations['WGT_MON']))
        self.assertEqual('F*WGT_MON', kill_spaces(s.Equations['DEM_MON']))

    def test_SetExogenous(self):
        mod = Model()
        us = Country(mod, 'USA', 'US')
        s = Sector(us, 'Household', 'HH')
        s.SetExogenous('varname', 'val')
        self.assertEqual([(s, 'varname', 'val'),], mod.Exogenous)

class TestCountry(TestCase):
    def test_AddSector(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        gov = DoNothingGovernment(can, 'Government', 'GOV')
        self.assertEqual(can.SectorList[0].ID, gov.ID)

    def test_LookupSector(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        gov = DoNothingGovernment(can, 'Government', 'GOV')
        hh = Household(can, 'Household', 'HH', .9, .2)
        self.assertEqual(can.LookupSector('HH').ID, hh.ID)
        self.assertEqual(can.LookupSector('GOV').ID, gov.ID)
        with self.assertRaises(KeyError):
            can.LookupSector('Smurf')


class TestMarket(TestCase):
    def test_GenerateEquations(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        mar = Market(can, 'Market', 'LAB')
        bus = Sector(can, 'Business', 'BUS')
        hh = Sector(can, 'Household', 'HH')
        bus.AddVariable('DEM_LAB', 'desc', 'x')
        hh.AddVariable('SUP_LAB', 'desc 2', '')
        mod.GenerateFullSectorCodes()
        mar.GenerateEquations()
        self.assertEqual(['-DEM_LAB', ], bus.CashFlows)
        self.assertEqual('x', bus.Equations['DEM_LAB'])
        self.assertEqual(['+SUP_LAB', ], hh.CashFlows)
        #self.assertEqual('BUS_DEM_LAB', hh.Equations['SUP_LAB'].strip())
        self.assertEqual('SUP_LAB', mar.Equations['SUP_HH'])
        self.assertEqual('LAB_SUP_HH', hh.Equations['SUP_LAB'].strip())

    def test_GenerateEquations_no_supply(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        mar = Market(can, 'Market', 'LAB')
        bus = Sector(can, 'Business', 'BUS')
        bus.AddVariable('DEM_LAB', 'desc', '')
        mod.GenerateFullSectorCodes()
        with self.assertRaises(ValueError):
            mar.GenerateEquations()

    def test_GenerateEquations_2_supply_fail(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        mar = Market(can, 'Market', 'LAB')
        bus = Sector(can, 'Business', 'BUS')
        hh = Sector(can, 'Household', 'HH')
        hh2 = Sector(can, 'Household', 'HH2')
        bus.AddVariable('DEM_LAB', 'desc', 'x')
        hh.AddVariable('SUP_LAB', 'desc 2', '')
        hh2.AddVariable('SUP_LAB', 'desc 2', '')
        mod.GenerateFullSectorCodes()
        with self.assertRaises(LogicError):
            mar.GenerateEquations()

    def test_GenerateEquations_2_supply(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        mar = Market(can, 'Market', 'LAB')
        bus = Sector(can, 'Business', 'BUS')
        hh = Sector(can, 'Household', 'HH')
        hh2 = Sector(can, 'Household', 'HH2')
        bus.AddVariable('DEM_LAB', 'desc', 'x')
        hh.AddVariable('SUP_LAB', 'desc 2', '')
        hh2.AddVariable('SUP_LAB', 'desc 2', '')
        mod.GenerateFullSectorCodes()
        mar.SupplyAllocation = [[(hh, 'SUP_LAB/2')], hh2]
        mar.GenerateEquations()
        self.assertEqual('SUP_LAB/2', mar.Equations['SUP_HH'])
        self.assertEqual('SUP_LAB-SUP_HH', kill_spaces(mar.Equations['SUP_HH2']))
        self.assertEqual('LAB_SUP_HH', hh.Equations['SUP_LAB'])
        self.assertEqual('LAB_SUP_HH2', hh2.Equations['SUP_LAB'])

    def test_GenerateEquations_2_supply_multicountry(self):
        mod = Model()
        can = Country(mod, 'Canada, Eh?', 'CA')
        US = Country(mod, 'USA! USA!', 'US')
        mar = Market(can, 'Market', 'LAB')
        bus = Sector(can, 'Business', 'BUS')
        hh = Sector(can, 'Household', 'HH')
        # Somehow, Americans are supplying labour in Canada...
        hh2 = Sector(US, 'Household', 'HH2')
        bus.AddVariable('DEM_LAB', 'desc', 'x')
        hh.AddVariable('SUP_LAB', 'desc 2', '')
        hh2.AddVariable('SUP_LAB', 'desc 2', '')
        mod.GenerateFullSectorCodes()
        mar.SupplyAllocation = [[(hh, 'SUP_LAB/2')], hh2]
        mar.GenerateEquations()
        self.assertEqual('SUP_LAB/2', mar.Equations['SUP_CA_HH'])
        self.assertEqual('SUP_LAB-SUP_CA_HH', kill_spaces(mar.Equations['SUP_US_HH2']))
        self.assertEqual('CA_LAB_SUP_CA_HH', hh.Equations['SUP_LAB'])
        self.assertIn('+SUP_LAB', hh.CashFlows)
        self.assertEqual('CA_LAB_SUP_US_HH2', hh2.Equations['SUP_CA_LAB'])
        self.assertIn('+SUP_CA_LAB', hh2.CashFlows)

    def test_GenerateEquations_2_supply_multicountry_2(self):
        mod = Model()
        can = Country(mod, 'Canada, Eh?', 'CA')
        US = Country(mod, 'USA! USA!', 'US')
        mar = Market(can, 'Market', 'LAB')
        bus = Sector(can, 'Business', 'BUS')
        hh = Sector(can, 'Household', 'HH')
        # Although we have two countries, both suppliers are from Canada
        hh2 = Sector(can, 'Household', 'HH2')
        bus.AddVariable('DEM_LAB', 'desc', 'x')
        hh.AddVariable('SUP_LAB', 'desc 2', '')
        hh2.AddVariable('SUP_LAB', 'desc 2', '')
        mod.GenerateFullSectorCodes()
        mar.SupplyAllocation = [[(hh, 'SUP_LAB/2')], hh2]
        mar.GenerateEquations()
        self.assertEqual('SUP_LAB/2', mar.Equations['SUP_CA_HH'])
        self.assertEqual('SUP_LAB-SUP_CA_HH', mar.Equations['SUP_CA_HH2'])
        self.assertEqual('CA_LAB_SUP_CA_HH', hh.Equations['SUP_LAB'])
        self.assertIn('+SUP_LAB', hh.CashFlows)
        self.assertEqual('CA_LAB_SUP_CA_HH2', hh2.Equations['SUP_LAB'])
        self.assertIn('+SUP_LAB', hh2.CashFlows)



    def test_GenerateTermsLowLevel(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        mar = Market(can, 'Market', 'LAB')
        bus = Sector(can, 'Business', 'BUS')
        bus.AddVariable('DEM_LAB', 'desc', '')
        mod.GenerateFullSectorCodes()
        mar.GenerateTermsLowLevel('DEM', 'Demand')
        self.assertEqual(['-DEM_LAB', ], bus.CashFlows)
        self.assertTrue('error' in bus.Equations['DEM_LAB'].lower())


    def test_GenerateTermsLowLevel_3(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        mar = Market(can, 'Market', 'LAB')
        with self.assertRaises(LogicError):
            mar.GenerateTermsLowLevel('Blam!', 'desc')

    def test_FixSingleSupply(self):
        mod = Model()
        can = Country(mod, 'Canada', 'Eh')
        mar = Market(can, 'Market', 'LAB')
        with self.assertRaises(LogicError):
            mar.FixSingleSupply()


class TestRegisterCashFlows(TestCase):
    def get_objects(self):
        mod = Model()
        co = Country(mod, 'name', 'code')
        sec1 = Sector(co, 'Sector1', 'SEC1')
        sec2 = Sector(co, 'Sector2', 'SEC2')
        return mod, sec1, sec2

    # Do not validate that variable exists when registering; only needs to exist when registered cash flows
    # are processed
    # def test_fail(self):
    #     mod, sec1, sec2 = self.get_objects()
    #     with self.assertRaises( KeyError):
    #         mod.RegisterCashFlow(sec1, sec2, 'DIV')

    def test_OK(self):
        mod, sec1, sec2 = self.get_objects()
        sec1.AddVariable('DIV', 'desc', '$1')
        mod.RegisterCashFlow(sec1, sec2, 'DIV')
        mod.GenerateFullSectorCodes()
        mod.GenerateEquations()
        mod.GenerateRegisteredCashFlows()
        mod.GenerateIncomeEquations()
        self.assertEqual('LAG_F+SEC1_DIV', kill_spaces(sec2.Equations['F']))
        self.assertEqual('LAG_F-SEC1_DIV', kill_spaces(sec1.Equations['F']))






