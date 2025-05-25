group "default" {
  targets = ["all"]
}

group "all" {
  targets = ["redis", "dbservice", "backend", "frontend", "opensearch", "jaeger", "otelcol", "prometheus", "grafana"]
}

# Service definitions

target "redis" {
  context = "."
  dockerfile = ""
  target = ""
}

target "dbservice" {
  context = "."
  dockerfile = ""
  target = ""
}

target "backend" {
  context = "."
  dockerfile = "backend/Dockerfile"
  target = ""
}

target "frontend" {
  context = "./frontend"
  dockerfile = "Dockerfile"
  target = ""
}

target "opensearch" {
  context = "."
  dockerfile = ""
  target = ""
}

target "jaeger" {
  context = "."
  dockerfile = ""
  target = ""
}

target "otelcol" {
  context = "."
  dockerfile = ""
  target = ""
}

target "prometheus" {
  context = "."
  dockerfile = ""
  target = ""
}

target "grafana" {
  context = "."
  dockerfile = ""
  target = ""
}
