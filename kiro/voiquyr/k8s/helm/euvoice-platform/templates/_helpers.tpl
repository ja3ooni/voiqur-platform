{{/*
Expand the name of the chart.
*/}}
{{- define "euvoice-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "euvoice-platform.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "euvoice-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "euvoice-platform.labels" -}}
helm.sh/chart: {{ include "euvoice-platform.chart" . }}
{{ include "euvoice-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
compliance.euvoice.ai/gdpr: "enabled"
compliance.euvoice.ai/ai-act: "enabled"
region: {{ .Values.global.region }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "euvoice-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "euvoice-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "euvoice-platform.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "euvoice-platform.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate image name with registry
*/}}
{{- define "euvoice-platform.image" -}}
{{- $registry := $.Values.global.imageRegistry -}}
{{- $repository := .repository -}}
{{- $tag := .tag | default "latest" -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}

{{/*
Generate environment variables for EU compliance
*/}}
{{- define "euvoice-platform.complianceEnv" -}}
- name: EU_COMPLIANCE_MODE
  value: "{{ .Values.global.gdprCompliance }}"
- name: AI_ACT_COMPLIANCE
  value: "{{ .Values.global.aiActCompliance }}"
- name: DATA_RESIDENCY
  value: "{{ .Values.global.dataResidency }}"
- name: REGION
  value: "{{ .Values.global.region }}"
- name: AUDIT_LOGGING_ENABLED
  value: "{{ .Values.security.auditLogging.enabled }}"
{{- end }}

{{/*
Generate resource requirements
*/}}
{{- define "euvoice-platform.resources" -}}
{{- if .resources }}
resources:
  {{- if .resources.limits }}
  limits:
    {{- toYaml .resources.limits | nindent 4 }}
  {{- end }}
  {{- if .resources.requests }}
  requests:
    {{- toYaml .resources.requests | nindent 4 }}
  {{- end }}
{{- end }}
{{- end }}

{{/*
Generate security context for EU compliance
*/}}
{{- define "euvoice-platform.securityContext" -}}
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
{{- end }}

{{/*
Generate pod security context
*/}}
{{- define "euvoice-platform.podSecurityContext" -}}
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
{{- end }}

{{/*
Generate affinity rules for EU compliance
*/}}
{{- define "euvoice-platform.affinity" -}}
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/region
          operator: In
          values:
          - {{ .Values.global.region }}
        - key: compliance.euvoice.ai/eu-node
          operator: In
          values:
          - "true"
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app.kubernetes.io/name
            operator: In
            values:
            - {{ include "euvoice-platform.name" . }}
        topologyKey: kubernetes.io/hostname
{{- end }}