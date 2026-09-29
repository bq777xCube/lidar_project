# Схемы решения

[Архитектура](architecture.svg) · [Порядок обработки](processing.svg) · [Запуск](deployment.svg)

SVG подходит для увеличения без потери качества, PNG используется в Markdown. DOT содержит редактируемый исходник. Рисунки описывают существующий код и сценарии запуска.

Пересборка с установленным Graphviz:

```bash
dot -Tsvg docs/diagrams/architecture.dot -o docs/diagrams/architecture.svg
dot -Tpng -Gdpi=135 docs/diagrams/architecture.dot -o docs/diagrams/architecture.png
```

Graphviz не требуется для работы детектора.
