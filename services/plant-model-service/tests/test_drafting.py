from app.configurations import demo_integrated_configuration_model
from app.drafting import STANDARD_PROFILE, master_for


def test_every_current_object_has_symbol_master():
    model = demo_integrated_configuration_model()
    keys = [master_for(obj).key for obj in model.objects]
    assert len(keys) == len(model.objects)


def test_drafting_profile_reserves_engineering_sheet_regions():
    assert STANDARD_PROFILE.margin > 0
    assert STANDARD_PROFILE.title_block_height >= 60
    assert STANDARD_PROFILE.grid_columns >= 6
    assert STANDARD_PROFILE.grid_rows >= 4


def test_symbol_master_has_declared_size():
    model = demo_integrated_configuration_model()
    for obj in model.objects:
        master = master_for(obj)
        assert master.width > 0
        assert master.height > 0
