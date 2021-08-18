import os
import copy
import numpy as np
import pytest
import pandas as pd
import tempfile
import logging

from allensdk.brain_observatory.behavior.behavior_project_cache \
    import VisualBehaviorOphysProjectCache
from allensdk.test.brain_observatory.behavior.conftest import get_resources_dir

from allensdk.brain_observatory.behavior.behavior_project_cache.\
    tables.util.experiments_table_utils import (
        add_experience_level_to_experiment_table,
        add_passive_flag_to_ophys_experiment_table,
        add_image_set_to_experiment_table)

from allensdk.brain_observatory.behavior.metadata.behavior_metadata import \
    BehaviorMetadata

from allensdk.brain_observatory.behavior.behavior_project_cache.tables \
    .util.prior_exposure_processing import \
    get_prior_exposures_to_session_type, \
    get_prior_exposures_to_image_set, \
    get_prior_exposures_to_omissions


@pytest.fixture(scope='session')
def behavior_session_id_list():
    return list(range(1,9))

@pytest.fixture(scope='session')
def session_name_lookup(behavior_session_id_list):
    return {ii: f'session_{ii}'
            for ii in behavior_session_id_list}

@pytest.fixture(scope='session')
def date_of_acquisition_lookup(behavior_session_id_list):
    return {ii: np.datetime64(f'2020-02-{ii:02d}')
            for ii in behavior_session_id_list}


@pytest.fixture(scope='session')
def session_type_lookup(behavior_session_id_list):
    rng = np.random.default_rng(871231)
    possible = ('TRAINING_1_gratings',
                'OPHYS_1_images_A',
                'OPHYS_1_images_B')

    vals = rng.choice(possible,
                      size=len(behavior_session_id_list),
                      replace=True)

    return {ii: vv
            for ii, vv in zip(behavior_session_id_list,
                              vals)}

@pytest.fixture(scope='session')
def project_code_lookup(behavior_session_id_list):
    return {ii: 'code{ii}'
            for ii in behavior_session_id_list}

@pytest.fixture(scope='session')
def specimen_id_lookup(behavior_session_id_list):
     return {ii: 1111*ii
             for ii in behavior_session_id_list}

@pytest.fixture(scope='session')
def genotype_lookup(behavior_session_id_list):
    rng = np.random.default_rng(981232)
    possible = ('foo-SlcCre',
                'Vip-IRES-Cre/wt;Ai148(TIT2L-GC6f-ICL-tTA2)/wt',
                'bar',
                'foobar')
    chosen = rng.choice(possible,
                        size=len(behavior_session_id_list),
                        replace=True)
    return {ii: val
            for ii, val in zip(behavior_session_id_list, chosen)}


@pytest.fixture(scope='session')
def reporter_lookup(behavior_session_id_list):
    return {ii: f"Ai{90+ii}(TITL-GCaMP6f)"
            for ii in behavior_session_id_list}

@pytest.fixture(scope='session')
def driver_lookup(behavior_session_id_list):
    rng = np.random.default_rng(1723213)
    possible = (["aa"],
                ["aa", "bb"],
                ["cc"],
                ["cc", "dd"])
    chosen = rng.choice(possible,
                        size=len(behavior_session_id_list),
                        replace=True)
    return {ii: val
            for ii, val in zip(behavior_session_id_list,
                               chosen)}

@pytest.fixture(scope='session')
def behavior_session_data_fixture(behavior_session_id_list,
                                  session_name_lookup,
                                  date_of_acquisition_lookup,
                                  session_type_lookup,
                                  specimen_id_lookup,
                                  genotype_lookup,
                                  reporter_lookup,
                                  driver_lookup):

    behavior_session_list = []
    for s_id in behavior_session_id_list:

        genotype = genotype_lookup[s_id]
        driver = driver_lookup[s_id]
        reporter = reporter_lookup[s_id]
        date = date_of_acquisition_lookup[s_id]
        specimen_id = specimen_id_lookup[s_id]
        s_name = session_name_lookup[s_id]
        s_type = session_type_lookup[s_id]
        datum = {'behavior_session_id': s_id,
                 'session_name': s_name,
                 'date_of_acquisition': date,
                 'specimen_id': specimen_id,
                 'session_type': s_type,
                 'equipment_name': 'MESO2.0',
                 'donor_id': 20+s_id,
                 'full_genotype': genotype,
                 'sex': ['m', 'f'][s_id % 2],
                 'age_in_days': s_id*7,
                 'foraging_id': s_id+30,
                 'mouse_id': s_id+40,
                 'reporter_line': reporter,
                 'driver_line': driver}

        behavior_session_list.append(datum)

    return behavior_session_list

@pytest.fixture(scope='session')
def behavior_session_to_ophys_session_map(behavior_session_id_list):
    lookup = dict()
    ophys_id = 88
    for ii in range(0, len(behavior_session_id_list)):
        if ii%3 == 0:
            continue
        lookup[behavior_session_id_list[ii]] = ophys_id
        ophys_id += 1
    return lookup

@pytest.fixture(scope='session')
def ophys_session_to_experiment_map(behavior_session_to_ophys_session_map):
    lookup = dict()
    i0 = 1000
    dd = 5
    ophys_vals = list(behavior_session_to_ophys_session_map.values())
    ophys_vals.sort()
    for ii in ophys_vals:
        lookup[ii] = list(range(i0, i0+dd))
        i0 += dd

    return lookup


@pytest.fixture(scope='session')
def ophys_experiment_to_container_map(ophys_session_to_experiment_map):
    lookup = dict()
    container_id = 4000
    key_list = list(ophys_session_to_experiment_map.keys())
    key_list.sort()
    for key in key_list:
        experiment_list = ophys_session_to_experiment_map[key]
        for exp_id in experiment_list:
            local_list = []
            for ii in range(7):
                container_id += 1
                local_list.append(container_id)
            lookup[exp_id] = local_list
    return lookup


@pytest.fixture(scope='session')
def ophys_session_data_fixture(project_code_lookup,
                               session_name_lookup,
                               date_of_acquisition_lookup,
                               specimen_id_lookup,
                               session_type_lookup,
                               ophys_session_to_experiment_map,
                               ophys_experiment_to_container_map,
                               behavior_session_to_ophys_session_map):
    ophys_session_list = []
    ophys_session_id_list = list(ophys_session_to_experiment_map.keys())
    ophys_session_id_list.sort()
    for beh in behavior_session_to_ophys_session_map:
        o_session = behavior_session_to_ophys_session_map[beh]
        container_list = []
        for exp_id in ophys_session_to_experiment_map[o_session]:
            container_list += ophys_experiment_to_container_map[exp_id]

        datum = {'behavior_session_id': beh,
                 'project_code': project_code_lookup[beh],
                 'date_of_acquisition': date_of_acquisition_lookup[beh],
                 'session_name': session_name_lookup[beh],
                 'session_type': session_type_lookup[beh],
                 'ophys_experiment_id': ophys_session_to_experiment_map[o_session],
                 'ophys_container_id': container_list,
                 'specimen_id': 9*beh,
                 'ophys_session_id': o_session}

        ophys_session_list.append(datum)
    return ophys_session_list


@pytest.fixture(scope='session')
def ophys_experiment_fixture(ophys_session_data_fixture,
                             experiment_state_lookup,
                             container_state_lookup,
                             ophys_experiment_to_container_map):

    rng = np.random.default_rng(182312)

    isi_id = 4000
    ophys_experiment_list = []
    for ophys_session in ophys_session_data_fixture:
        for i_experiment in ophys_session['ophys_experiment_id']:
            for container_id in ophys_experiment_to_container_map[i_experiment]:
                datum = {'ophys_session_id': ophys_session['ophys_session_id'],
                         'session_type': ophys_session['session_type'],
                         'behavior_session_id': ophys_session['behavior_session_id'],
                         'ophys_container_id': container_id,
                         'container_workflow_state': container_state_lookup[container_id],
                         'experiment_workflow_state': experiment_state_lookup[i_experiment],
                         'session_name': ophys_session['session_name'],
                         'date_of_acquisition': ophys_session['date_of_acquisition'],
                         'isi_experiment_id': isi_id,
                         'imaging_depth': rng.integers(50, 200),
                         'targeted_tructure': 'VISp',
                         'published_at': ophys_session['date_of_acquisition'],
                         'ophys_experiment_id': i_experiment}
                ophys_experiment_list.append(datum)
    return ophys_experiment_list


@pytest.fixture(scope='session')
def container_state_lookup(ophys_experiment_to_container_map):
    rng = np.random.default_rng(66232)
    exp_id_list = list(ophys_experiment_to_container_map.keys())
    exp_id_list.sort()
    lookup = dict()
    for exp_id in exp_id_list:
        local_container_list = ophys_experiment_to_container_map[exp_id]
        for container_id in local_container_list:
            assert container_id not in lookup
            lookup[container_id] = 'junk'
        good_container = rng.choice(local_container_list)
        lookup[good_container] = 'published'
    return lookup


@pytest.fixture(scope='session')
def experiment_state_lookup(ophys_session_data_fixture):
    rng = np.random.default_rng(772312)
    exp_id_list = []
    for datum in ophys_session_data_fixture:
        for exp_id in datum['ophys_experiment_id']:
           if exp_id not in exp_id_list:
               exp_id_list.append(exp_id)
    lookup = dict()
    for exp_id in exp_id_list:
        lookup[exp_id] = ['passed', 'failed'][rng.integers(0, 2)]
    return lookup


@pytest.fixture()
def ophys_session_table(ophys_session_data_fixture):
    data = []
    index = []
    for datum in ophys_session_data_fixture:
        datum = copy.deepcopy(datum)
        index.append(datum.pop('ophys_session_id'))
        data.append(datum)

    df = pd.DataFrame(
             data,
             index=pd.Index(index, name='ophys_session_id'))
    return df


@pytest.fixture()
def behavior_session_table(behavior_session_data_fixture):
    data = []
    index = []
    for datum in behavior_session_data_fixture:
        datum = copy.deepcopy(datum)
        index.append(datum.pop('behavior_session_id'))
        data.append(datum)

    df = pd.DataFrame(
              data,
              index=pd.Index(index, name='behavior_session_id'))
    return df


@pytest.fixture()
def expected_behavior_session_table(behavior_session_table,
                                    ophys_session_data_fixture,
                                    mock_api,
                                    container_state_lookup,
                                    experiment_state_lookup,
                                    ophys_experiment_to_container_map):
    df = behavior_session_table.copy(deep=True)

    df['reporter_line'] = df['reporter_line'].apply(
        BehaviorMetadata.parse_reporter_line)
    df['cre_line'] = df['full_genotype'].apply(
        BehaviorMetadata.parse_cre_line)
    df['indicator'] = df['reporter_line'].apply(
        BehaviorMetadata.parse_indicator)

    df['prior_exposures_to_session_type'] = \
        get_prior_exposures_to_session_type(df=df)
    df['prior_exposures_to_image_set'] = \
        get_prior_exposures_to_image_set(df=df)
    df['prior_exposures_to_omissions'] = \
        get_prior_exposures_to_omissions(
            df=df,
            fetch_api=mock_api)

    df['session_name_behavior'] = df['session_name']
    df = df.drop(['session_name'], axis=1)
    df['specimen_id_behavior'] = df['specimen_id']
    df = df.drop(['specimen_id'], axis=1)

    df['project_code'] = None
    df['ophys_session_id'] = None
    df['session_name_ophys'] = None
    df['ophys_experiment_id'] = None
    df['ophys_container_id'] = None
    df['specimen_id_ophys'] = None

    session_number = []
    for v in df['session_type'].values:
        if 'OPHYS' in v:
            session_number.append(1)
        else:
            session_number.append(None)
    df['session_number'] = session_number

    for ophys_session in ophys_session_data_fixture:
        index = ophys_session['behavior_session_id']
        df.at[index, 'project_code'] = ophys_session['project_code']
        df.at[index, 'ophys_session_id'] = ophys_session['ophys_session_id']
        df.at[index, 'session_name_ophys'] = ophys_session['session_name']

        container_id_list = set()
        exp_id_list = set()
        for exp_id in ophys_session['ophys_experiment_id']:
            exp_id_list.add(exp_id)  # because SessionsTable does not filter on experiment state
            if experiment_state_lookup[exp_id] != 'passed':
                continue
            for container_id in ophys_experiment_to_container_map[exp_id]:
                if container_state_lookup[container_id] == 'published':
                    container_id_list.add(container_id)
        exp_id_list = list(exp_id_list)
        exp_id_list.sort()
        container_id_list = list(container_id_list)
        container_id_list.sort()

        df.at[index, 'ophys_container_id'] = container_id_list
        df.at[index, 'ophys_experiment_id'] = exp_id_list
        df.at[index, 'specimen_id_ophys'] = ophys_session['specimen_id']

    df['ophys_session_id'] = df['ophys_session_id'].astype(float)

    return df

@pytest.fixture()
def expected_experiments_table(ophys_experiments_table,
                               container_state_lookup,
                               experiment_state_lookup,
                               behavior_session_data_fixture):

    """
        datum = {'behavior_session_id': s_id,
                 'session_name': s_name,
                 'date_of_acquisition': date,
                 'specimen_id': specimen_id,
                 'session_type': s_type,
                 'equipment_name': 'MESO2.0',
                 'donor_id': 20+s_id,
                 'full_genotype': genotype,
                 'sex': ['m', 'f'][s_id % 2],
                 'age_in_days': s_id*7,
                 'foraging_id': s_id+30,
                 'mouse_id': s_id+40,
                 'reporter_line': reporter,
                 'driver_line': driver}
    """

    behavior_id_to_session = dict()
    for datum in behavior_session_data_fixture:
        behavior_id_to_session[datum['behavior_session_id']] = datum

    expected = ophys_experiments_table.copy(deep=True)

    expected = expected.query("experiment_workflow_state=='passed'")
    expected = expected.query("container_workflow_state=='published'")

    for col_name in ('equipment_name',
                     'donor_id',
                     'full_genotype',
                     'mouse_id',
                     'driver_line',
                     'sex',
                     'age_in_days',
                     'foraging_id'):
        values = []
        for ii in expected['behavior_session_id'].values:
            session = behavior_id_to_session[ii]
            values.append(session[col_name])
        expected[col_name] = values

    session_number = []
    for v in expected['session_type'].values:
        if 'OPHYS' in v:
            session_number.append(1)
        else:
            session_number.append(None)
    expected['session_number'] = session_number

    expected['prior_exposures_to_image_set'] = \
            get_prior_exposures_to_image_set(expected)
    expected = add_experience_level_to_experiment_table(expected)
    expected = add_passive_flag_to_ophys_experiment_table(expected)
    expected = add_image_set_to_experiment_table(expected)

    return expected


@pytest.fixture()
def ophys_experiments_table(ophys_experiment_fixture):
    data = []
    index = []
    for datum in ophys_experiment_fixture:
        datum = copy.deepcopy(datum)
        index.append(datum.pop('ophys_experiment_id'))
        data.append(datum)

    df = pd.DataFrame(
              data,
              index=pd.Index(index, name='ophys_experiment_id'))
    return df


@pytest.fixture
def mock_api(ophys_session_table,
             behavior_session_table,
             ophys_experiments_table):

    class MockApi:

        def get_ophys_session_table(self):
            return ophys_session_table

        def get_behavior_session_table(self):
            return behavior_session_table

        def get_ophys_experiment_table(self):
            return ophys_experiments_table

        def get_session_data(self, ophys_session_id):
            return ophys_session_id

        def get_behavior_stage_parameters(self, foraging_ids):
            return {x: {} for x in foraging_ids}

    return MockApi


@pytest.fixture
def TempdirBehaviorCache(mock_api, request):
    temp_dir = tempfile.TemporaryDirectory()
    manifest = os.path.join(temp_dir.name, "manifest.json")
    yield VisualBehaviorOphysProjectCache(fetch_api=mock_api(),
                                          cache=request.param,
                                          manifest=manifest)
    temp_dir.cleanup()


def safe_df_comparison(expected: pd.DataFrame, obtained:pd.DataFrame):
    """
    Compare two dataframes in a way that is agnostic to column order
    and datatype of NULL values
    """
    msg = ''
    if len(obtained.columns) != len(expected.columns):
        msg += 'column mis-match\n'
        msg += 'obtained columns\n'
        msg += f'{obtained.columns}\n'
        msg += 'expected columns\n'
        msg += f'{expected.columns}\n'
        raise RuntimeError(msg)

    if not expected.index.equals(obtained.index):
        msg += 'index mis-match\n'
        msg += 'expected index\n'
        msg += f'{expected.index}\n'
        msg += 'obtained index\n'
        msg += f'{obtained.index}\n'
        raise RuntimeError(msg)

    for col in expected.columns:
        expected_null = expected[col].isnull()
        obtained_null = obtained[col].isnull()
        if not expected_null.equals(obtained_null):
            msg += f'\n{col} not null at same point in '
            msg += 'obtained and expected\n'
            continue
        expected_valid = expected[~expected_null]
        obtained_valid = obtained[~obtained_null]
        if not expected_valid.index.equals(obtained_valid.index):
            msg += f'\nindex mismatch in non-null when checking '
            msg += f'{col}\n'
        for index_val in expected_valid.index.values:
            e = expected_valid.at[index_val, col]
            o = obtained_valid.at[index_val, col]
            if not e==o:
                msg += f'\n{col}\n'
                msg += f'expected: {e}\n'
                msg += f'obtained: {o}\n'
    if msg != '':
        raise RuntimeError(msg)


@pytest.mark.skip('SFD')
@pytest.mark.parametrize("TempdirBehaviorCache", [True, False], indirect=True)
def test_get_ophys_session_table(TempdirBehaviorCache, session_table):
    cache = TempdirBehaviorCache
    obtained = cache.get_ophys_session_table()
    if cache.cache:
        path = cache.manifest.path_info.get("ophys_sessions").get("spec")
        assert os.path.exists(path)

    expected_path = os.path.join(get_resources_dir(), 'project_metadata',
                                 'expected')
    expected = pd.read_pickle(os.path.join(expected_path,
                                           'ophys_session_table.pkl'))

    pd.testing.assert_frame_equal(expected, obtained)


@pytest.mark.parametrize("TempdirBehaviorCache", [True, False], indirect=True)
def test_get_behavior_table(TempdirBehaviorCache,
                            expected_behavior_session_table,
                            container_state_lookup,
                            experiment_state_lookup,
                            ophys_experiment_to_container_map):
    cache = TempdirBehaviorCache
    obtained = cache.get_behavior_session_table()
    expected = expected_behavior_session_table
    if cache.cache:
        path = cache.manifest.path_info.get("behavior_sessions").get("spec")
        assert os.path.exists(path)

    safe_df_comparison(expected, obtained)


@pytest.mark.parametrize("TempdirBehaviorCache", [True, False], indirect=True)
def test_get_experiments_table(TempdirBehaviorCache,
                               expected_experiments_table):
    cache = TempdirBehaviorCache
    obtained = cache.get_ophys_experiment_table(passed_only=True)
    if cache.cache:
        path = cache.manifest.path_info.get("ophys_experiments").get("spec")
        assert os.path.exists(path)

    safe_df_comparison(expected_experiments_table, obtained)


@pytest.mark.skip('SFD')
@pytest.mark.parametrize("TempdirBehaviorCache", [True], indirect=True)
def test_session_table_reads_from_cache(TempdirBehaviorCache, session_table,
                                        caplog):
    caplog.set_level(logging.INFO, logger="call_caching")
    cache = TempdirBehaviorCache
    cache.get_ophys_session_table()
    expected_first = [
        ('call_caching', logging.INFO, 'Reading data from cache'),
        ('call_caching', logging.INFO, 'No cache file found.'),
        ('call_caching', logging.INFO, 'Fetching data from remote'),
        ('call_caching', logging.INFO, 'Writing data to cache'),
        ('call_caching', logging.INFO, 'Reading data from cache'),
        ('call_caching', logging.INFO, 'Reading data from cache'),
        ('call_caching', logging.INFO, 'No cache file found.'),
        ('call_caching', logging.INFO, 'Fetching data from remote'),
        ('call_caching', logging.INFO, 'Writing data to cache'),
        ('call_caching', logging.INFO, 'Reading data from cache')]
    assert expected_first == caplog.record_tuples
    caplog.clear()
    cache.get_ophys_session_table()
    assert [expected_first[0], expected_first[-1]] == caplog.record_tuples


@pytest.mark.skip('SFD')
@pytest.mark.parametrize("TempdirBehaviorCache", [True], indirect=True)
def test_behavior_table_reads_from_cache(TempdirBehaviorCache, behavior_table,
                                         caplog):
    caplog.set_level(logging.INFO, logger="call_caching")
    cache = TempdirBehaviorCache
    cache.get_behavior_session_table()
    expected_first = [
        ('call_caching', logging.INFO, 'Reading data from cache'),
        ('call_caching', logging.INFO, 'No cache file found.'),
        ('call_caching', logging.INFO, 'Fetching data from remote'),
        ('call_caching', logging.INFO, 'Writing data to cache'),
        ('call_caching', logging.INFO, 'Reading data from cache'),
        ('call_caching', logging.INFO, 'Reading data from cache'),
        ('call_caching', logging.INFO, 'No cache file found.'),
        ('call_caching', logging.INFO, 'Fetching data from remote'),
        ('call_caching', logging.INFO, 'Writing data to cache'),
        ('call_caching', logging.INFO, 'Reading data from cache')]
    assert expected_first == caplog.record_tuples
    caplog.clear()
    cache.get_behavior_session_table()
    assert [expected_first[0], expected_first[-1]] == caplog.record_tuples


@pytest.mark.skip('SFD')
@pytest.mark.parametrize("TempdirBehaviorCache", [True, False], indirect=True)
def test_get_ophys_session_table_by_experiment(TempdirBehaviorCache):
    expected = (pd.DataFrame({"ophys_session_id": [1, 1],
                              "ophys_experiment_id": [5, 6]})
                .set_index("ophys_experiment_id"))
    actual = TempdirBehaviorCache.get_ophys_session_table(
        index_column="ophys_experiment_id")[
        ["ophys_session_id"]]
    pd.testing.assert_frame_equal(expected, actual)


@pytest.mark.skip('SFD')
@pytest.mark.parametrize("TempdirBehaviorCache", [True], indirect=True)
def test_cloud_manifest_errors(TempdirBehaviorCache):
    """
    Test that methods which should not exist for BehaviorProjectCaches
    that are not backed by CloudCaches raise NotImplementedError
    """
    msg = 'Method {mname} does not exist for this '
    msg += 'VisualBehaviorOphysProjectCache, which is based on MockApi'
    with pytest.raises(NotImplementedError,
                       match=msg.format(mname='construct_local_manifest')):
        TempdirBehaviorCache.construct_local_manifest()

    with pytest.raises(NotImplementedError,
                       match=msg.format(mname='compare_manifests')):
        TempdirBehaviorCache.compare_manifests('a', 'b')

    with pytest.raises(NotImplementedError,
                       match=msg.format(mname='load_latest_manifest')):
        TempdirBehaviorCache.load_latest_manifest()

    this_msg = msg.format(mname='latest_downloaded_manifest_file')
    with pytest.raises(NotImplementedError,
                       match=this_msg):
        TempdirBehaviorCache.latest_downloaded_manifest_file()

    with pytest.raises(NotImplementedError,
                       match=msg.format(mname='latest_manifest_file')):
        TempdirBehaviorCache.latest_manifest_file()

    with pytest.raises(NotImplementedError,
                       match=msg.format(mname='load_manifest')):
        TempdirBehaviorCache.load_manifest('a')

    with pytest.raises(NotImplementedError,
                       match=msg.format(mname='current_manifest')):
        TempdirBehaviorCache.current_manifest()

    this_msg = msg.format(mname='list_all_downloaded_manifests')
    with pytest.raises(NotImplementedError,
                       match=this_msg):
        TempdirBehaviorCache.list_all_downloaded_manifests()

    this_msg = msg.format(mname='list_manifest_file_names')
    with pytest.raises(NotImplementedError,
                       match=this_msg):
        TempdirBehaviorCache.list_manifest_file_names()
