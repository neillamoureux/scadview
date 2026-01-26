import argparse

from trimesh.creation import cylinder


def create_mesh(radius: float = 10.0, height: float = 20.0):
    return cylinder(radius=radius, height=height)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=float, default=10.0)
    parser.add_argument("--height", type=float, default=20.0)
    parser.add_argument("--out", required=True, help="Output file, e.g. model.stl")
    args = parser.parse_args()

    mesh = create_mesh(radius=args.radius, height=args.height)
    mesh.export(args.out)


if __name__ == "__main__":
    main()
