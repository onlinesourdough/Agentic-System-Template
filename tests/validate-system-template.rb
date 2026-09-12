#!/usr/bin/env ruby
# Seed-only structural checks; no agent behavior or downstream System audit.
require 'psych'
require 'pathname'

root = Pathname.new(ARGV.fetch(0, File.expand_path('..', __dir__))).realpath
expected = ['.agents/skills/agentic-system-template/SKILL.md']
skills = Dir.glob(root.join('.agents/skills/**/SKILL.md').to_s).sort
abort 'Unexpected seed skill inventory' unless skills.map { |p| Pathname.new(p).relative_path_from(root).to_s } == expected

# SemVer 2.0 core, optional prerelease and build identifiers.
number = '(?:0|[1-9][0-9]*)'
identifier = '(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)'
semver = /\A#{number}\.#{number}\.#{number}(?:-#{identifier}(?:\.#{identifier})*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\z/
allowed = %w[name description license allowed-tools metadata]

skills.each do |path|
  lines = File.readlines(path)
  abort "Missing frontmatter: #{path}" unless lines.shift == "---\n"
  finish = lines.index("---\n")
  abort "Unclosed frontmatter: #{path}" unless finish
  frontmatter = lines.take(finish).join
  data = Psych.safe_load(frontmatter)
  abort "Invalid schema: #{path}" unless data.is_a?(Hash) && (data.keys - allowed).empty?
  abort "Name mismatch: #{path}" unless data['name'] == File.basename(File.dirname(path))
  abort "Missing description: #{path}" unless data['description'].is_a?(String) && !data['description'].strip.empty?
  metadata = data['metadata']
  abort "Invalid metadata: #{path}" unless metadata.is_a?(Hash) && metadata.all? { |k, v| k.is_a?(String) && v.is_a?(String) }
  version = metadata['version']
  abort "Invalid metadata.version: #{path}" unless version.is_a?(String) && semver.match?(version)

  # Parse YAML nodes to enforce quoting and reject ambiguous duplicate keys.
  check_mapping = lambda do |node|
    if node.is_a?(Psych::Nodes::Mapping)
      pairs = node.children.each_slice(2).to_a
      keys = pairs.map { |k, _| k.value }
      abort "Duplicate YAML keys: #{path}" unless keys.uniq == keys
      pairs.each { |_, value| check_mapping.call(value) }
    end
  end
  mapping = Psych.parse(frontmatter).root
  check_mapping.call(mapping)
  metadata_node = mapping.children.each_slice(2).find { |key, _| key.value == 'metadata' }[1]
  version_node = metadata_node.children.each_slice(2).find { |key, _| key.value == 'version' }[1]
  abort "metadata.version must be quoted: #{path}" unless version_node.quoted
end

Dir.glob(root.join('**/*.md').to_s, File::FNM_DOTMATCH).each do |path|
  next if Pathname.new(path).each_filename.include?('.git')
  File.read(path).scan(/\]\(([^)]+)\)/).flatten.each do |target|
    next if target.match?(/\A(?:https?:|mailto:|#)/)
    target = target.split('#', 2).first
    abort "Broken local link #{target}: #{path}" unless File.exist?(File.expand_path(target, File.dirname(path)))
  end
end
puts "system template validation: PASS (#{skills.length} skill; schema, quoted SemVer, inventory, links)"
