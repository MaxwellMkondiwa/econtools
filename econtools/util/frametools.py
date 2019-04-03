from typing import Optional, Union

import pandas as pd
import numpy as np

from econtools.util.gentools import force_iterable


def stata_merge(left: pd.DataFrame, right: pd.DataFrame,
                assertval: Optional[int] = None, gen: str = '_m',
                **kwargs) -> pd.DataFrame:
    """
    Replicates Stata's generation of a flag for merge status.
        1 = Unmatched row from the left
        2 = Unmatched row from the right
        3 = Matched row

    Parameters
    -----------
    assertval, 1, 2, or 3 (None)
        Assert that all rows matched according to the given code. Note that not
        all values of assertval will make sense with all possible how arguments
        passed to pandas.merge

    gen, str ('_m')
        Name of the categorical variable.

    kwargs,
        Any standard keyword arg for pandas.merge.
    """
    # Tmp variables needed for merge status variable
    left_tmp = 'tmpa'
    right_tmp = 'tmpb'
    while left_tmp in left.columns:
        left_tmp += 'a'
    while right_tmp in right.columns:
        right_tmp += 'b'
    # Try this copying stuff to avoid altering the original dataframes
    copy_left, copy_right = left.copy(), right.copy()
    copy_left[left_tmp] = 1
    copy_right[right_tmp] = 2
    # Actual merge
    new = pd.merge(copy_left, copy_right, **kwargs)
    # Generate merge status flag
    new[gen] = new[left_tmp].add(new[right_tmp], fill_value=0)
    # Clean up tmp variables
    del new[left_tmp], new[right_tmp]

    # Show distribution of rows by merge status
    if assertval:
        try:
            assert (new[gen] == assertval).min()
        except AssertionError:
            print("Merge assertion is false!")
            print(new.groupby(gen).size() / new.shape[0])
            raise
        else:
            del new[gen]
    else:
        print(new.groupby(gen).size() / new.shape[0])

    return new


def group_id(df, cols=None, name='group_id', merge=False):
    """
    Generate a unique numeric ID from several columns of a DataFrame.

    merge,
        If True, add the new 'group_id' column to a copy of the original
        DataFrame. Otherwise, only return the cross-walk of `cols` and the id.
    """
    if not cols:
        cols = df.columns.tolist()

    if name in df.columns:
        raise ValueError("ID name '{}' is a column name.".format(name))

    unique_df = df[cols].drop_duplicates().reset_index(drop=True)
    unique_df.index.name = name
    unique_df = unique_df.reset_index()

    if merge:
        unique_df = stata_merge(df, unique_df, on=cols, how='left',
                                assertval=3)
        new_i, new_j = unique_df.shape
        old_i, old_j = df.shape
        assert new_i == old_i and new_j == old_j + 1
        unique_df.index = df.index

    return unique_df


def winsorize(df, by, p=(.01, .99)):
    """Drop variables in `by' outside quantiles `p`."""
    # TODO: Some kind of warning/error if too fine of quantiles are
    #       requested for the number of rows, e.g. .99 with 5 rows.
    df = df.copy()

    by = force_iterable(by)

    # Allow different cutoffs for different variables
    if hasattr(p[0], '__iter__'):
        assert len(p) == len(by)
    else:
        p = [p] * len(by)

    survive_winsor = np.array([True] * df.shape[0])

    for idx, col in enumerate(by):
        cuts = df[col].quantile(p[idx]).values
        survive_this = np.logical_and(df[col] >= cuts[0], df[col] <= cuts[1])
        survive_winsor = np.minimum(survive_winsor, survive_this)

    df = df[survive_winsor]

    return df


def df_to_list(df: Union[list, pd.DataFrame]) -> list:
    """ Turn rows of DataFrame to list of Series objects """
    if type(df) is list:
        return df
    elif type(df) is pd.DataFrame:
        return [b for a, b in df.iterrows()]
    else:
        raise(ValueError)
