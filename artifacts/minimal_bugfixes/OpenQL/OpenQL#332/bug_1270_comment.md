Fixer: "Move unitary logic into separate compile unit, to prevent its dependencies (notably Eigen) from having to be parsed/template-expanded for every other compile unit as well.".