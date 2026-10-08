"""Find groups of duplicate pictures among the fingerprinted ones."""
import numpy as np

# How many of the 64 bits of two perceptual hashes may differ. Calibrated on 763 real photos of 17 places,
# by looking at the pairs: 0-2 bits were always the same picture saved at another size; 6-12 bits were the
# same scene with a small change (a neighbouring frame of a series, a crop); from 14 bits on the photos
# were unrelated, and the number of such pairs grows fast (17 pairs at 14 bits, 308 at 18).
SAME_PICTURE_DISTANCE = 4
SIMILAR_DISTANCE = 12

EXACT, SAME_PICTURE, SIMILAR = 1, 2, 3      # group levels


def distance(phash_a, phash_b):
    """How many of the 64 bits differ between two perceptual hashes."""
    return (int(phash_a, 16) ^ int(phash_b, 16)).bit_count()


def identical_file_sets(images):
    """Sets of byte-identical files (equal sha256), two or more files each; most widespread first."""
    by_sha = {}
    for image in images:
        by_sha.setdefault(image["sha256"], []).append(image)
    sets = [files for files in by_sha.values() if len(files) > 1]
    sets.sort(key=lambda files: (-len({f["place"] for f in files}), -len(files)))
    return sets


def _components(images, max_distance):
    """Split picture indexes into sets joined by equal sha256 or by hashes at most `max_distance` bits apart.

    Joining is transitive: A~B and B~C puts A, B and C together. Every picture is compared with every other.
    """
    parent = list(range(len(images)))

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    first_with_sha = {}
    for index, image in enumerate(images):
        other = first_with_sha.setdefault(image["sha256"], index)
        if other != index:
            parent[root(index)] = root(other)

    hashed = [index for index, image in enumerate(images) if image["phash"]]
    values = np.array([int(images[index]["phash"], 16) for index in hashed], dtype=np.uint64)
    for position in range(len(hashed) - 1):
        differing_bits = np.bitwise_count(values[position] ^ values[position + 1:])
        for offset in np.nonzero(differing_bits <= max_distance)[0]:
            parent[root(hashed[position])] = root(hashed[position + 1 + int(offset)])

    components = {}
    for index in range(len(images)):
        components.setdefault(root(index), set()).add(index)
    return [frozenset(members) for members in components.values() if len(members) > 1]


def find_groups(images, similar_distance=SIMILAR_DISTANCE):
    """Group the pictures that show the same thing.

    `images` are rows with id, place, sha256, phash. Returns [{"level", "members"}], most widespread first:
      EXACT         all files in the group are byte-identical;
      SAME_PICTURE  the same picture in different files (hashes within SAME_PICTURE_DISTANCE);
      SIMILAR       held together only by looser matches (up to `similar_distance`): a candidate to look at.
    """
    certain = set(_components(images, SAME_PICTURE_DISTANCE))
    groups = []
    for component in _components(images, similar_distance):
        members = [images[index] for index in sorted(component)]
        if component not in certain:
            level = SIMILAR
        elif len({m["sha256"] for m in members}) == 1:
            level = EXACT
        else:
            level = SAME_PICTURE
        groups.append({"level": level, "members": members})
    groups.sort(key=lambda g: (g["level"], -len({m["place"] for m in g["members"]}), -len(g["members"])))
    return groups


def place_matrix(images, groups):
    """Count shared pictures per pair of places, separately for certain duplicates and for candidates.

    Returns (places, matrix). matrix[a][b] is [certain, similar]: the number of EXACT/SAME_PICTURE groups
    and of SIMILAR groups that have a file in both places. For a == b it counts the groups with two or
    more files inside that one place.
    """
    places = sorted({image["place"] for image in images})
    matrix = {a: {b: [0, 0] for b in places} for a in places}
    for group in groups:
        per_place = {}
        for member in group["members"]:
            per_place[member["place"]] = per_place.get(member["place"], 0) + 1
        column = 1 if group["level"] == SIMILAR else 0
        for a in per_place:
            for b in per_place:
                if a != b or per_place[a] > 1:
                    matrix[a][b][column] += 1
    return places, matrix
