"""
Metrics for algorithm effectivness (Precission, Recall, F1-Score / Hamming-Threshold)

Effectiveness is a set of metrics to evaluate the performance of information retrieval systems.
Effectiveness metrics assess the ability of a system to retrieve relevant items while
minimizing the retrieval of non-relevant ones.

We calculate effectiveness of near-duplicate retrieval by measuring recall, precision, and
f1-score at hamming distance thresholds 0 to max_threshold for each query input.
We determine the max_threshold dynamically as 1/4th total bitlength of the compact binary code.

Given a simprint csv `ìnfile` with the following required fields:
    id: The unique id of the media file
    code: Hex encoded similarity preserving compact binary code
    file: The root relative file path of the media file

We don´t care about additional fields in the simprint file.

Example simprint file:
    id;code;file
    0;fd79f57fbd7de57f;0000000/0010078.mp3
    1;fd79f57ffd7df57f;0000000/z0010078_compressed-medium.mp3
    ...
    33;747cbc7734feb497;073912.mp3

We load the simprint file into a pandas dataframe and augment it with the following fields:
    cluster: the cluster name (if any) derived from the file field
    transform: the name of the transformation (if any) derived from the file field
    is_original: a bolean indicating whether the file is an original untransformed file

Ground truth:
    The ground truth for measurments is derived from the naming conventions of the `file`
    field.

    Clusters:
        The first path segment (if any) is the identifier of a cluster of media files that are
        considered to be near-duplicates.
        Example: file 0000000/0010078.mp3 = cluster 0000000

    Transformations:
        The last underscore ('_') seperated segment (if any) minus exclusing the file extension
        is an  optional identifier for a specific transformation.
        Example: file z0010078_compressed-medium.mp3 = transformation compressed-medium

    Originals:
        The first file (when sorted lexocographically by filename) in a cluster of variations
        is the original file. The order of entries in a simprint file is:
        Clustered files first, ordered by cluster name, each cluster ordered by file name and
        then the top level distractor files ordered by filename.

Query input selection:
    originals: only original (first files) from cluster folders are queried
    clusters: all files from cluster folders are queried
    all: each media file is queried

Query result sets selection:
    duplicates: the source cluster of the queried input
    clusters: all clusters of dataset (other clusters serve as distractors)
    distractors: search against distractor result-set should not return results
    all: all files exclusing the query file are used as result set


Implementation Notes:
    For efficient processing we create the following intermediary data structurs:
        1. ground_truth:
            Ground truth data derived from the clustering as a mapping of
            query_file_id: ((hamming_distance, result_file_id), ...)
            Ground truth results include all files from a cluster and are sorted by lowest to
            hightest hamming distance
        2. query_results:
            Result data of running query inputs once against all media files with max hamming
            distance as a mapping of:
            query_file_id ((hamming_distance, result_file_id), ...)
            Query results include all files with up to (including) max_threshold hamming
            distance and are sorted by lowest to hightest hamming distance.

    Given gound_truths and query_results we calculate recal, precision, and
    f1-scores per query at thresholds 0 to max_trhreshold.

TODO: Calculate effectiveness per transformation
TODO: Settle on query input selection and query result set
"""
from pathlib import Path
import pandas as pd
from hexhamming import hamming_distance_string as hamming_distance
from twinspect.metrics.hamming import HammingHero
from twinspect.tools import result_path
from twinspect.metrics.utils import update_json


def effectiveness(simprint_path):
    # type: (str|Path) -> dict
    """Calculate precission, recall and f1-score for simprint csv file"""
    simprint_path = Path(simprint_path)
    df_simprints = load_simprints(simprint_path)

    # Inferr max hamming threshold as 1/4 of the code length
    code = df_simprints.at[0, "code"]
    bitlength = int((len(code) / 2) * 8)
    max_threshold = bitlength // 4

    # Compute ground truth and query results
    df_ground_truth = ground_truth(df_simprints)
    hh = HammingHero(simprint_path)
    df_query_results = hh.compute_queries(max_threshold)

    # Evaluate computed ground truth and query results
    result = evaluate(df_ground_truth, df_query_results, max_threshold)

    # Store evaluaion results
    algo, dataset, checksum = simprint_path.name.split("-")[:3]
    metrics_path = result_path(algo, dataset, "json", tag="metrics")
    result = {
        "algorithm": algo,
        "dataset": dataset,
        "checksum": checksum,
        "metrics": {
            "effectiveness": result,
        },
    }
    update_json(metrics_path, result)
    return result


def load_simprints(simprint_path):
    # type: (str|Path) -> pd.DataFrame
    """Loads simprint csv into pandas dataframe and augment with cluster, transform, is_original.

    The file field is parsed to create fields for cluster and transformation ids.
    We also add an is_original boolean field to indicate where a file is an original file.
    """
    # Load the simprint CSV file into a pandas DataFrame
    simprints = pd.read_csv(
        simprint_path,
        delimiter=";",
        dtype={"id": int, "code": str, "file": str, "size": int, "time": int},
    )

    # Extract cluster information
    simprints["cluster"] = (
        simprints["file"].str.split("/").str[0].where(simprints["file"].str.contains("/"), None)
    )

    # Extract transformation information
    simprints["transform"] = (
        simprints["file"]
        .str.split("_")
        .str[-1]
        .str.split(".")
        .str[0]
        .where(simprints["file"].str.contains("_"), None)
    )

    # Initialize the is_original column with False values
    simprints["is_original"] = False

    # Identify cluster files
    cluster_files = simprints["cluster"].notnull()

    # Set the is_original value to True for the first entry in every new cluster
    simprints.loc[
        cluster_files & simprints["cluster"].ne(simprints["cluster"].shift()), "is_original"
    ] = True

    return simprints


def ground_truth(df):
    # type: (pd.DataFrame) -> pd.DataFrame
    """Calculate the ground truth data from the simprints DataFrame.

    A row in the ground truth data includes the id of the query file and the results of the
    query as list of tuples (hamming_distance, file_id). The results for a given query file
    are all other files within the cluster except for itself. Results are ordered by
    hamming_distance. Top levels files without cluster of clusters with only one file have an
    empty result list.
    """
    df["ground_truth"] = df.apply(
        lambda x: [
            (hamming_distance(x["code"], y["code"]), y["id"])
            for _, y in df[df["cluster"] == x["cluster"]].iterrows()
            if y["id"] != x["id"]
        ]
        if pd.notna(x["cluster"])
        else [],
        axis=1,
    )
    df["ground_truth"] = df["ground_truth"].apply(lambda x: sorted(x, key=lambda y: y[0]))
    return df[["id", "ground_truth"]]


def evaluate(df_ground_truth, df_query_result, max_threshold):
    # type: (pd.DataFrame, pd.DataFrame, int) -> list[dict]
    """
    Evaluate precision, recall and f1-score for all thresholdss from 0 - max_threshold.

    Each row in the input dataframes must include the `id` of the query file and the `ground_truth`
    or `query_result query as sequence of (hamming_distance, file_id) results.

    The Result is a dictionary of the form:

    {
        "effectiveness": [
            {
              "threshold": 0,
              "precision": 0.95,
              "recall": 0.92,
              "f1_score": 0.935
            },
            ...
            {
              "threshold": N,
              "precision": P_N,
              "recall": R_N,
              "f1_score": F1_N
            }
        ]
    }

    :param df_ground_truth: DataFrame with ground truth data e.g. df[["id", "ground_truth"]]
    :param df_query_result: DataFrame with query result data e.g. df[["id", "query_result"]]
    :param max_threshold: Maximum threshold of query results
    :return: dict
    """
    # Merge ground truth and query result dataframes on the 'id' column
    df = df_ground_truth.merge(df_query_result, on="id")

    result = []

    # Iterate through all thresholds from 0 to max_threshold
    for threshold in range(max_threshold + 1):
        tp = 0
        fp = 0
        fn = 0

        # Iterate through each row in the merged dataframe
        for _, row in df.iterrows():
            ground_truth = set(
                file_id
                for hamming_distance, file_id in row["ground_truth"]
                if hamming_distance <= threshold
            )
            query_result = set(
                file_id
                for hamming_distance, file_id in row["query_result"]
                if hamming_distance <= threshold
            )

            tp += len(ground_truth.intersection(query_result))
            fp += len(query_result.difference(ground_truth))
            fn += len(ground_truth.difference(query_result))

        # Calculate precision, recall, and F1-score
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        # Append the result to the effectiveness list
        result.append(
            {"threshold": threshold, "precision": precision, "recall": recall, "f1_score": f1_score}
        )

    return result
