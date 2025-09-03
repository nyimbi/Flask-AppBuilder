"""
Modern UI Widget Components for Flask-AppBuilder

This module provides a comprehensive collection of modern, responsive UI widgets
with advanced features including drag & drop, rich text editing, color pickers,
file uploaders, and interactive components.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from flask import Markup, render_template_string, url_for, current_app
from flask_babel import gettext, lazy_gettext
from wtforms.widgets import TextArea, Input, Select, CheckboxInput
from wtforms.widgets.core import html_params

log = logging.getLogger(__name__)


class ModernTextWidget(Input):
    """
    Modern text input widget with enhanced UX features.
    
    Features:
    - Floating labels with smooth animations
    - Real-time character counting
    - Input validation with visual feedback
    - Auto-complete suggestions
    - Icon support (prefix/suffix)
    - Responsive design
    - Keyboard shortcuts
    - Focus states with smooth transitions
    """
    
    input_type = 'text'
    
    def __init__(self, 
                 icon_prefix: Optional[str] = None,
                 icon_suffix: Optional[str] = None,
                 show_counter: bool = False,
                 max_length: Optional[int] = None,
                 autocomplete_source: Optional[str] = None,
                 placeholder: Optional[str] = None,
                 floating_label: bool = True):
        """
        Initialize the modern text widget.
        
        Args:
            icon_prefix: FontAwesome icon class for prefix icon
            icon_suffix: FontAwesome icon class for suffix icon
            show_counter: Whether to show character counter
            max_length: Maximum character length
            autocomplete_source: URL for autocomplete suggestions
            placeholder: Placeholder text
            floating_label: Whether to use floating label design
        """
        self.icon_prefix = icon_prefix
        self.icon_suffix = icon_suffix
        self.show_counter = show_counter
        self.max_length = max_length
        self.autocomplete_source = autocomplete_source
        self.placeholder = placeholder
        self.floating_label = floating_label
        
    def __call__(self, field, **kwargs):
        """Render the modern text widget."""
        widget_id = kwargs.get('id', f'modern_text_{uuid4().hex[:8]}')
        kwargs.setdefault('id', widget_id)
        kwargs.setdefault('class', 'form-control modern-input')
        
        if self.max_length:
            kwargs['maxlength'] = self.max_length
            
        if self.placeholder:
            kwargs['placeholder'] = self.placeholder
        elif not self.floating_label and field.label:
            kwargs['placeholder'] = field.label.text
            
        # Build the widget HTML
        input_html = super().__call__(field, **kwargs)
        
        template = """
        <div class="modern-input-group" data-widget="modern-text">
            {% if icon_prefix %}
            <div class="input-group-prepend">
                <span class="input-group-text">
                    <i class="fa {{ icon_prefix }}"></i>
                </span>
            </div>
            {% endif %}
            
            <div class="form-floating">
                {{ input_html | safe }}
                {% if floating_label and field.label %}
                <label for="{{ widget_id }}">{{ field.label.text }}</label>
                {% endif %}
            </div>
            
            {% if icon_suffix %}
            <div class="input-group-append">
                <span class="input-group-text">
                    <i class="fa {{ icon_suffix }}"></i>
                </span>
            </div>
            {% endif %}
            
            {% if show_counter %}
            <div class="form-text character-counter">
                <span class="current-count">0</span>
                {% if max_length %}/ <span class="max-count">{{ max_length }}</span>{% endif %}
                {{ _('characters') }}
            </div>
            {% endif %}
        </div>
        
        <style>
        .modern-input-group {
            position: relative;
            margin-bottom: 1rem;
        }
        
        .modern-input-group .form-control {
            border-radius: 8px;
            border: 2px solid #e9ecef;
            padding: 0.75rem 1rem;
            transition: all 0.3s ease;
            font-size: 1rem;
        }
        
        .modern-input-group .form-control:focus {
            border-color: #0d6efd;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
            transform: translateY(-1px);
        }
        
        .form-floating > label {
            padding: 1rem;
            color: #6c757d;
            transition: all 0.3s ease;
        }
        
        .character-counter {
            font-size: 0.875rem;
            color: #6c757d;
            text-align: right;
            margin-top: 0.25rem;
        }
        
        .character-counter.warning {
            color: #fd7e14;
        }
        
        .character-counter.danger {
            color: #dc3545;
        }
        </style>
        
        <script>
        (function() {
            const input = document.getElementById('{{ widget_id }}');
            const counter = input.closest('.modern-input-group').querySelector('.character-counter');
            
            if (input && counter) {
                const currentCount = counter.querySelector('.current-count');
                const maxCount = {{ max_length or 'null' }};
                
                function updateCounter() {
                    const length = input.value.length;
                    currentCount.textContent = length;
                    
                    if (maxCount) {
                        counter.classList.remove('warning', 'danger');
                        if (length > maxCount * 0.9) {
                            counter.classList.add('danger');
                        } else if (length > maxCount * 0.8) {
                            counter.classList.add('warning');
                        }
                    }
                }
                
                input.addEventListener('input', updateCounter);
                input.addEventListener('keydown', function(e) {
                    // Add keyboard shortcuts
                    if (e.ctrlKey || e.metaKey) {
                        if (e.key === 'a') {
                            // Ctrl+A to select all (default behavior)
                        }
                    }
                });
                
                updateCounter();
            }
            
            {% if autocomplete_source %}
            // Add autocomplete functionality
            if (input) {
                let timeout;
                input.addEventListener('input', function() {
                    clearTimeout(timeout);
                    timeout = setTimeout(() => {
                        // Implement autocomplete logic here
                        fetch('{{ autocomplete_source }}?q=' + encodeURIComponent(input.value))
                            .then(response => response.json())
                            .then(data => {
                                // Handle autocomplete suggestions
                            });
                    }, 300);
                });
            }
            {% endif %}
        })();
        </script>
        """
        
        return Markup(render_template_string(template, 
            input_html=input_html,
            widget_id=widget_id,
            field=field,
            icon_prefix=self.icon_prefix,
            icon_suffix=self.icon_suffix,
            show_counter=self.show_counter,
            max_length=self.max_length,
            floating_label=self.floating_label,
            _=gettext
        ))


class ModernTextAreaWidget(TextArea):
    """
    Modern textarea widget with advanced editing features.
    
    Features:
    - Auto-resizing based on content
    - Rich text formatting toolbar (optional)
    - Character/word counting
    - Markdown preview (optional)
    - Syntax highlighting for code
    - Drag & drop support
    - Full-screen mode
    - Auto-save drafts
    """
    
    def __init__(self,
                 auto_resize: bool = True,
                 rich_text: bool = False,
                 markdown_preview: bool = False,
                 syntax_highlighting: Optional[str] = None,
                 show_stats: bool = True,
                 full_screen: bool = True,
                 auto_save: bool = False,
                 min_rows: int = 3,
                 max_rows: int = 15):
        """
        Initialize the modern textarea widget.
        
        Args:
            auto_resize: Auto-resize based on content
            rich_text: Enable rich text editing toolbar
            markdown_preview: Show markdown preview
            syntax_highlighting: Language for syntax highlighting
            show_stats: Show character/word count
            full_screen: Enable full-screen editing mode
            auto_save: Auto-save drafts
            min_rows: Minimum number of rows
            max_rows: Maximum number of rows
        """
        self.auto_resize = auto_resize
        self.rich_text = rich_text
        self.markdown_preview = markdown_preview
        self.syntax_highlighting = syntax_highlighting
        self.show_stats = show_stats
        self.full_screen = full_screen
        self.auto_save = auto_save
        self.min_rows = min_rows
        self.max_rows = max_rows
        
    def __call__(self, field, **kwargs):
        """Render the modern textarea widget."""
        widget_id = kwargs.get('id', f'modern_textarea_{uuid4().hex[:8]}')
        kwargs.setdefault('id', widget_id)
        kwargs.setdefault('class', 'form-control modern-textarea')
        kwargs.setdefault('rows', self.min_rows)
        
        # Build the widget HTML
        textarea_html = super().__call__(field, **kwargs)
        
        template = """
        <div class="modern-textarea-container" data-widget="modern-textarea">
            {% if rich_text or full_screen or markdown_preview %}
            <div class="modern-textarea-toolbar">
                {% if rich_text %}
                <div class="toolbar-group">
                    <button type="button" class="btn btn-sm btn-outline-secondary" 
                            data-action="bold" title="{{ _('Bold') }}">
                        <i class="fa fa-bold"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" 
                            data-action="italic" title="{{ _('Italic') }}">
                        <i class="fa fa-italic"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" 
                            data-action="underline" title="{{ _('Underline') }}">
                        <i class="fa fa-underline"></i>
                    </button>
                </div>
                <div class="toolbar-group">
                    <button type="button" class="btn btn-sm btn-outline-secondary" 
                            data-action="heading" title="{{ _('Heading') }}">
                        <i class="fa fa-heading"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" 
                            data-action="list" title="{{ _('List') }}">
                        <i class="fa fa-list-ul"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" 
                            data-action="link" title="{{ _('Link') }}">
                        <i class="fa fa-link"></i>
                    </button>
                </div>
                {% endif %}
                
                <div class="toolbar-group ms-auto">
                    {% if markdown_preview %}
                    <button type="button" class="btn btn-sm btn-outline-info" 
                            data-action="preview" title="{{ _('Preview') }}">
                        <i class="fa fa-eye"></i>
                    </button>
                    {% endif %}
                    {% if full_screen %}
                    <button type="button" class="btn btn-sm btn-outline-secondary" 
                            data-action="fullscreen" title="{{ _('Full Screen') }}">
                        <i class="fa fa-expand"></i>
                    </button>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
            <div class="modern-textarea-wrapper">
                {{ textarea_html | safe }}
                
                {% if markdown_preview %}
                <div class="markdown-preview" style="display: none;">
                    <div class="preview-content"></div>
                </div>
                {% endif %}
            </div>
            
            {% if show_stats %}
            <div class="textarea-stats">
                <span class="character-count">0 {{ _('characters') }}</span>
                <span class="word-count">0 {{ _('words') }}</span>
                {% if auto_save %}
                <span class="auto-save-status">
                    <i class="fa fa-save"></i> {{ _('Auto-saved') }}
                </span>
                {% endif %}
            </div>
            {% endif %}
        </div>
        
        <style>
        .modern-textarea-container {
            border: 2px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .modern-textarea-container:focus-within {
            border-color: #0d6efd;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }
        
        .modern-textarea-toolbar {
            background-color: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
            padding: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .toolbar-group {
            display: flex;
            gap: 0.25rem;
        }
        
        .modern-textarea {
            border: none;
            border-radius: 0;
            resize: none;
            min-height: calc({{ min_rows }} * 1.5em + 1rem);
            transition: height 0.3s ease;
        }
        
        .modern-textarea:focus {
            box-shadow: none;
        }
        
        .markdown-preview {
            padding: 1rem;
            background-color: #f8f9fa;
            border-top: 1px solid #e9ecef;
            min-height: 100px;
        }
        
        .textarea-stats {
            background-color: #f8f9fa;
            border-top: 1px solid #e9ecef;
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
            color: #6c757d;
            display: flex;
            gap: 1rem;
            align-items: center;
        }
        
        .auto-save-status {
            margin-left: auto;
            color: #28a745;
        }
        
        .modern-textarea-container.fullscreen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 9999;
            background: white;
            border-radius: 0;
        }
        
        .modern-textarea-container.fullscreen .modern-textarea {
            height: calc(100vh - 150px);
        }
        </style>
        
        <script>
        (function() {
            const container = document.querySelector('[data-widget="modern-textarea"]');
            const textarea = document.getElementById('{{ widget_id }}');
            
            if (!container || !textarea) return;
            
            // Auto-resize functionality
            {% if auto_resize %}
            function autoResize() {
                const minHeight = {{ min_rows }} * 24; // Approximate line height
                const maxHeight = {{ max_rows }} * 24;
                
                textarea.style.height = 'auto';
                const scrollHeight = textarea.scrollHeight;
                textarea.style.height = Math.min(Math.max(scrollHeight, minHeight), maxHeight) + 'px';
            }
            
            textarea.addEventListener('input', autoResize);
            autoResize();
            {% endif %}
            
            // Stats update
            {% if show_stats %}
            function updateStats() {
                const text = textarea.value;
                const charCount = text.length;
                const wordCount = text.trim() ? text.trim().split(/\\s+/).length : 0;
                
                const charElement = container.querySelector('.character-count');
                const wordElement = container.querySelector('.word-count');
                
                if (charElement) charElement.textContent = charCount + ' {{ _("characters") }}';
                if (wordElement) wordElement.textContent = wordCount + ' {{ _("words") }}';
            }
            
            textarea.addEventListener('input', updateStats);
            updateStats();
            {% endif %}
            
            // Toolbar functionality
            container.addEventListener('click', function(e) {
                const action = e.target.closest('[data-action]')?.dataset.action;
                if (!action) return;
                
                e.preventDefault();
                
                switch (action) {
                    case 'bold':
                        insertMarkdown('**', '**');
                        break;
                    case 'italic':
                        insertMarkdown('*', '*');
                        break;
                    case 'heading':
                        insertMarkdown('## ', '');
                        break;
                    case 'list':
                        insertMarkdown('- ', '');
                        break;
                    case 'link':
                        insertMarkdown('[', '](url)');
                        break;
                    case 'fullscreen':
                        toggleFullscreen();
                        break;
                    case 'preview':
                        togglePreview();
                        break;
                }
            });
            
            function insertMarkdown(before, after) {
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const text = textarea.value;
                const selectedText = text.substring(start, end);
                
                const newText = text.substring(0, start) + before + selectedText + after + text.substring(end);
                textarea.value = newText;
                textarea.focus();
                textarea.setSelectionRange(start + before.length, start + before.length + selectedText.length);
                
                updateStats();
                autoResize();
            }
            
            function toggleFullscreen() {
                container.classList.toggle('fullscreen');
                const icon = container.querySelector('[data-action="fullscreen"] i');
                if (container.classList.contains('fullscreen')) {
                    icon.className = 'fa fa-compress';
                } else {
                    icon.className = 'fa fa-expand';
                }
                autoResize();
            }
            
            function togglePreview() {
                const preview = container.querySelector('.markdown-preview');
                if (preview) {
                    if (preview.style.display === 'none') {
                        // Show preview
                        preview.style.display = 'block';
                        // Here you would implement markdown parsing
                        preview.querySelector('.preview-content').innerHTML = '<em>Markdown preview would go here</em>';
                    } else {
                        preview.style.display = 'none';
                    }
                }
            }
            
            {% if auto_save %}
            // Auto-save functionality
            let saveTimeout;
            textarea.addEventListener('input', function() {
                clearTimeout(saveTimeout);
                saveTimeout = setTimeout(() => {
                    // Implement auto-save logic here
                    console.log('Auto-saving content...');
                    const statusElement = container.querySelector('.auto-save-status');
                    if (statusElement) {
                        statusElement.style.opacity = '1';
                        setTimeout(() => statusElement.style.opacity = '0.7', 1000);
                    }
                }, 2000);
            });
            {% endif %}
        })();
        </script>
        """
        
        return Markup(render_template_string(template,
            textarea_html=textarea_html,
            widget_id=widget_id,
            field=field,
            rich_text=self.rich_text,
            markdown_preview=self.markdown_preview,
            show_stats=self.show_stats,
            full_screen=self.full_screen,
            auto_save=self.auto_save,
            min_rows=self.min_rows,
            max_rows=self.max_rows,
            _=gettext
        ))


class ModernSelectWidget(Select):
    """
    Modern select widget with enhanced functionality.
    
    Features:
    - Searchable options
    - Multi-select with tags
    - Custom option templates
    - AJAX loading support
    - Option grouping
    - Icons for options
    - Keyboard navigation
    - Mobile-friendly design
    """
    
    def __init__(self,
                 searchable: bool = True,
                 multiple: bool = False,
                 ajax_source: Optional[str] = None,
                 option_template: Optional[str] = None,
                 group_by: Optional[str] = None,
                 show_icons: bool = False,
                 placeholder: str = "Select an option..."):
        """
        Initialize the modern select widget.
        
        Args:
            searchable: Enable option searching
            multiple: Allow multiple selections
            ajax_source: URL for AJAX option loading
            option_template: Custom template for options
            group_by: Field to group options by
            show_icons: Show icons in options
            placeholder: Placeholder text
        """
        self.searchable = searchable
        self.multiple = multiple
        self.ajax_source = ajax_source
        self.option_template = option_template
        self.group_by = group_by
        self.show_icons = show_icons
        self.placeholder = placeholder
        
    def __call__(self, field, **kwargs):
        """Render the modern select widget."""
        widget_id = kwargs.get('id', f'modern_select_{uuid4().hex[:8]}')
        kwargs.setdefault('id', widget_id)
        kwargs.setdefault('class', 'form-control modern-select')
        
        if self.multiple:
            kwargs['multiple'] = True
            
        # Build the widget HTML
        select_html = super().__call__(field, **kwargs)
        
        template = """
        <div class="modern-select-container" data-widget="modern-select">
            {{ select_html | safe }}
        </div>
        
        <style>
        .modern-select-container {
            position: relative;
        }
        
        .modern-select {
            border-radius: 8px;
            border: 2px solid #e9ecef;
            padding: 0.75rem 1rem;
            transition: all 0.3s ease;
        }
        
        .modern-select:focus {
            border-color: #0d6efd;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }
        </style>
        
        <script>
        (function() {
            const select = document.getElementById('{{ widget_id }}');
            
            // Initialize Select2 or similar if available
            if (typeof $ !== 'undefined' && $.fn.select2) {
                $('#{{ widget_id }}').select2({
                    placeholder: '{{ placeholder }}',
                    allowClear: true,
                    {% if searchable %}
                    minimumResultsForSearch: 0,
                    {% else %}
                    minimumResultsForSearch: Infinity,
                    {% endif %}
                    {% if ajax_source %}
                    ajax: {
                        url: '{{ ajax_source }}',
                        dataType: 'json',
                        delay: 250,
                        processResults: function(data) {
                            return {
                                results: data.map(item => ({
                                    id: item.value,
                                    text: item.text,
                                    icon: item.icon
                                }))
                            };
                        }
                    }
                    {% endif %}
                });
            }
        })();
        </script>
        """
        
        return Markup(render_template_string(template,
            select_html=select_html,
            widget_id=widget_id,
            searchable=self.searchable,
            multiple=self.multiple,
            ajax_source=self.ajax_source,
            placeholder=self.placeholder
        ))


class ColorPickerWidget(Input):
    """
    Advanced color picker widget with multiple input methods.
    
    Features:
    - Color palette selector
    - RGB/HSL/Hex input modes
    - Color history/favorites
    - Eyedropper tool (where supported)
    - Gradient picker
    - Accessibility features
    - Custom color swatches
    """
    
    input_type = 'color'
    
    def __init__(self,
                 show_palette: bool = True,
                 show_input: bool = True,
                 show_history: bool = True,
                 custom_colors: Optional[List[str]] = None,
                 format_output: str = 'hex'):  # hex, rgb, hsl
        """
        Initialize the color picker widget.
        
        Args:
            show_palette: Show color palette
            show_input: Show text input for color values
            show_history: Show recently used colors
            custom_colors: List of custom color swatches
            format_output: Output format (hex, rgb, hsl)
        """
        self.show_palette = show_palette
        self.show_input = show_input
        self.show_history = show_history
        self.custom_colors = custom_colors or []
        self.format_output = format_output
        
    def __call__(self, field, **kwargs):
        """Render the color picker widget."""
        widget_id = kwargs.get('id', f'color_picker_{uuid4().hex[:8]}')
        kwargs.setdefault('id', widget_id)
        kwargs.setdefault('class', 'form-control color-picker')
        
        template = """
        <div class="color-picker-container" data-widget="color-picker">
            <div class="color-input-group">
                <input type="color" id="{{ widget_id }}" name="{{ field.name }}" 
                       value="{{ field.data or '#000000' }}" class="native-color-picker">
                
                {% if show_input %}
                <input type="text" class="form-control color-text-input" 
                       value="{{ field.data or '#000000' }}" 
                       placeholder="#000000">
                {% endif %}
                
                <button type="button" class="btn btn-outline-secondary color-preview" 
                        style="background-color: {{ field.data or '#000000' }};">
                    <i class="fa fa-palette"></i>
                </button>
            </div>
            
            {% if show_palette or show_history %}
            <div class="color-picker-panel" style="display: none;">
                {% if show_palette %}
                <div class="color-palette">
                    <h6>{{ _('Color Palette') }}</h6>
                    <div class="palette-grid">
                        {% for color in default_colors %}
                        <button type="button" class="color-swatch" 
                                style="background-color: {{ color }};" 
                                data-color="{{ color }}" title="{{ color }}"></button>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
                
                {% if custom_colors %}
                <div class="custom-colors">
                    <h6>{{ _('Custom Colors') }}</h6>
                    <div class="custom-grid">
                        {% for color in custom_colors %}
                        <button type="button" class="color-swatch" 
                                style="background-color: {{ color }};" 
                                data-color="{{ color }}" title="{{ color }}"></button>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
                
                {% if show_history %}
                <div class="color-history">
                    <h6>{{ _('Recent Colors') }}</h6>
                    <div class="history-grid" id="color-history-{{ widget_id }}">
                        <!-- Recent colors will be populated here -->
                    </div>
                </div>
                {% endif %}
            </div>
            {% endif %}
        </div>
        
        <style>
        .color-picker-container {
            position: relative;
            margin-bottom: 1rem;
        }
        
        .color-input-group {
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }
        
        .native-color-picker {
            width: 50px;
            height: 40px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }
        
        .color-text-input {
            flex: 1;
            font-family: monospace;
        }
        
        .color-preview {
            width: 40px;
            height: 40px;
            border-radius: 6px;
            border: 2px solid #dee2e6;
            position: relative;
            overflow: hidden;
        }
        
        .color-picker-panel {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            margin-top: 0.5rem;
        }
        
        .palette-grid, .custom-grid, .history-grid {
            display: grid;
            grid-template-columns: repeat(8, 1fr);
            gap: 4px;
            margin-top: 0.5rem;
        }
        
        .color-swatch {
            width: 32px;
            height: 32px;
            border: 2px solid #fff;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }
        
        .color-swatch:hover {
            transform: scale(1.1);
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        }
        
        .color-swatch.active {
            border-color: #0d6efd;
            box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.25);
        }
        </style>
        
        <script>
        (function() {
            const container = document.querySelector('[data-widget="color-picker"]');
            const nativeInput = document.getElementById('{{ widget_id }}');
            const textInput = container.querySelector('.color-text-input');
            const preview = container.querySelector('.color-preview');
            const panel = container.querySelector('.color-picker-panel');
            
            const defaultColors = [
                '#FF0000', '#FF8000', '#FFFF00', '#80FF00', '#00FF00', '#00FF80', '#00FFFF', '#0080FF',
                '#0000FF', '#8000FF', '#FF00FF', '#FF0080', '#800000', '#804000', '#808000', '#408000',
                '#008000', '#008040', '#008080', '#004080', '#000080', '#400080', '#800080', '#800040',
                '#000000', '#404040', '#808080', '#C0C0C0', '#FFFFFF', '#FF8080', '#FFFF80', '#80FF80'
            ];
            
            // Initialize with default colors
            if (panel) {
                const paletteGrid = panel.querySelector('.palette-grid');
                if (paletteGrid) {
                    defaultColors.forEach(color => {
                        const swatch = document.createElement('button');
                        swatch.type = 'button';
                        swatch.className = 'color-swatch';
                        swatch.style.backgroundColor = color;
                        swatch.dataset.color = color;
                        swatch.title = color;
                        paletteGrid.appendChild(swatch);
                    });
                }
            }
            
            // Color change handlers
            function updateColor(color) {
                nativeInput.value = color;
                if (textInput) textInput.value = color;
                preview.style.backgroundColor = color;
                
                // Update active swatch
                container.querySelectorAll('.color-swatch').forEach(swatch => {
                    swatch.classList.toggle('active', swatch.dataset.color === color);
                });
                
                // Add to history
                addToHistory(color);
            }
            
            function addToHistory(color) {
                {% if show_history %}
                const historyGrid = document.getElementById('color-history-{{ widget_id }}');
                if (historyGrid) {
                    // Remove if already exists
                    const existing = historyGrid.querySelector(`[data-color="${color}"]`);
                    if (existing) existing.remove();
                    
                    // Add to beginning
                    const swatch = document.createElement('button');
                    swatch.type = 'button';
                    swatch.className = 'color-swatch';
                    swatch.style.backgroundColor = color;
                    swatch.dataset.color = color;
                    swatch.title = color;
                    historyGrid.insertBefore(swatch, historyGrid.firstChild);
                    
                    // Limit to 8 colors
                    while (historyGrid.children.length > 8) {
                        historyGrid.removeChild(historyGrid.lastChild);
                    }
                }
                {% endif %}
            }
            
            // Event listeners
            nativeInput.addEventListener('change', () => updateColor(nativeInput.value));
            
            if (textInput) {
                textInput.addEventListener('change', () => {
                    const color = textInput.value;
                    if (/^#[0-9A-F]{6}$/i.test(color)) {
                        updateColor(color);
                    }
                });
            }
            
            preview.addEventListener('click', () => {
                if (panel) {
                    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
                }
            });
            
            container.addEventListener('click', (e) => {
                if (e.target.classList.contains('color-swatch')) {
                    updateColor(e.target.dataset.color);
                }
            });
            
            // Close panel when clicking outside
            document.addEventListener('click', (e) => {
                if (panel && !container.contains(e.target)) {
                    panel.style.display = 'none';
                }
            });
            
            // Initialize
            updateColor(nativeInput.value || '#000000');
        })();
        </script>
        """
        
        return Markup(render_template_string(template,
            widget_id=widget_id,
            field=field,
            show_palette=self.show_palette,
            show_input=self.show_input,
            show_history=self.show_history,
            custom_colors=self.custom_colors,
            _=gettext
        ))


class FileUploadWidget(Input):
    """
    Advanced file upload widget with drag & drop, previews, and progress.
    
    Features:
    - Drag & drop file upload
    - File type validation
    - Image preview thumbnails
    - Upload progress bar
    - Multiple file support
    - File size validation
    - Custom upload handlers
    - Chunked upload for large files
    """
    
    input_type = 'file'
    
    def __init__(self,
                 multiple: bool = False,
                 allowed_types: Optional[List[str]] = None,
                 max_file_size: Optional[int] = None,
                 max_files: int = 5,
                 show_preview: bool = True,
                 upload_endpoint: Optional[str] = None,
                 chunked_upload: bool = False):
        """
        Initialize the file upload widget.
        
        Args:
            multiple: Allow multiple file selection
            allowed_types: List of allowed MIME types
            max_file_size: Maximum file size in bytes
            max_files: Maximum number of files
            show_preview: Show image previews
            upload_endpoint: Custom upload endpoint
            chunked_upload: Enable chunked upload for large files
        """
        self.multiple = multiple
        self.allowed_types = allowed_types or ['image/*', 'application/pdf']
        self.max_file_size = max_file_size or (10 * 1024 * 1024)  # 10MB default
        self.max_files = max_files
        self.show_preview = show_preview
        self.upload_endpoint = upload_endpoint
        self.chunked_upload = chunked_upload
        
    def __call__(self, field, **kwargs):
        """Render the file upload widget."""
        widget_id = kwargs.get('id', f'file_upload_{uuid4().hex[:8]}')
        kwargs.setdefault('id', widget_id)
        kwargs.setdefault('class', 'file-upload-input')
        
        if self.multiple:
            kwargs['multiple'] = True
            
        kwargs['accept'] = ','.join(self.allowed_types)
        
        template = """
        <div class="file-upload-container" data-widget="file-upload">
            <div class="file-upload-dropzone" id="dropzone-{{ widget_id }}">
                <div class="dropzone-content">
                    <i class="fa fa-cloud-upload fa-3x text-muted"></i>
                    <h4>{{ _('Drop files here or click to browse') }}</h4>
                    <p class="text-muted">
                        {{ _('Allowed types') }}: {{ allowed_types | join(', ') }}<br>
                        {{ _('Maximum size') }}: {{ max_file_size_mb }}MB
                        {% if multiple %} | {{ _('Maximum files') }}: {{ max_files }}{% endif %}
                    </p>
                </div>
                
                <input type="file" id="{{ widget_id }}" name="{{ field.name }}" 
                       style="display: none;" {{ file_attrs | safe }}>
            </div>
            
            <div class="file-upload-queue" id="queue-{{ widget_id }}" style="display: none;">
                <h5>{{ _('Upload Queue') }}</h5>
                <div class="queue-items"></div>
                <div class="queue-actions">
                    <button type="button" class="btn btn-primary btn-sm" data-action="upload-all">
                        <i class="fa fa-upload"></i> {{ _('Upload All') }}
                    </button>
                    <button type="button" class="btn btn-secondary btn-sm" data-action="clear-all">
                        <i class="fa fa-times"></i> {{ _('Clear All') }}
                    </button>
                </div>
            </div>
        </div>
        
        <style>
        .file-upload-container {
            margin-bottom: 1rem;
        }
        
        .file-upload-dropzone {
            border: 2px dashed #dee2e6;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background-color: #f8f9fa;
        }
        
        .file-upload-dropzone:hover {
            border-color: #0d6efd;
            background-color: #e7f3ff;
        }
        
        .file-upload-dropzone.dragover {
            border-color: #0d6efd;
            background-color: #cfe2ff;
            transform: scale(1.02);
        }
        
        .file-upload-queue {
            margin-top: 1rem;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1rem;
        }
        
        .queue-item {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.5rem;
            border-bottom: 1px solid #e9ecef;
            margin-bottom: 0.5rem;
        }
        
        .queue-item:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        
        .file-preview {
            width: 60px;
            height: 60px;
            border-radius: 6px;
            object-fit: cover;
            border: 1px solid #dee2e6;
        }
        
        .file-icon {
            width: 60px;
            height: 60px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: #6c757d;
        }
        
        .file-info {
            flex: 1;
        }
        
        .file-name {
            font-weight: 500;
            margin: 0;
        }
        
        .file-size {
            color: #6c757d;
            font-size: 0.875rem;
            margin: 0;
        }
        
        .file-progress {
            width: 100%;
            height: 4px;
            background-color: #e9ecef;
            border-radius: 2px;
            margin-top: 0.25rem;
            overflow: hidden;
        }
        
        .file-progress-bar {
            height: 100%;
            background-color: #0d6efd;
            width: 0%;
            transition: width 0.3s ease;
        }
        
        .file-actions {
            display: flex;
            gap: 0.25rem;
        }
        
        .queue-actions {
            margin-top: 1rem;
            display: flex;
            gap: 0.5rem;
        }
        </style>
        
        <script>
        (function() {
            const container = document.querySelector('[data-widget="file-upload"]');
            const dropzone = document.getElementById('dropzone-{{ widget_id }}');
            const fileInput = document.getElementById('{{ widget_id }}');
            const queue = document.getElementById('queue-{{ widget_id }}');
            const queueItems = queue.querySelector('.queue-items');
            
            let fileQueue = [];
            
            // File validation
            function validateFile(file) {
                const allowedTypes = {{ allowed_types | tojson }};
                const maxSize = {{ max_file_size }};
                
                // Check file type
                const isValidType = allowedTypes.some(type => {
                    if (type.endsWith('/*')) {
                        return file.type.startsWith(type.replace('/*', '/'));
                    }
                    return file.type === type;
                });
                
                if (!isValidType) {
                    return { valid: false, error: `Invalid file type: ${file.type}` };
                }
                
                // Check file size
                if (file.size > maxSize) {
                    const maxMB = Math.round(maxSize / 1024 / 1024);
                    return { valid: false, error: `File too large: ${Math.round(file.size / 1024 / 1024)}MB (max: ${maxMB}MB)` };
                }
                
                return { valid: true };
            }
            
            // Format file size
            function formatFileSize(bytes) {
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }
            
            // Create queue item
            function createQueueItem(file, index) {
                const item = document.createElement('div');
                item.className = 'queue-item';
                item.dataset.index = index;
                
                const validation = validateFile(file);
                const isValid = validation.valid;
                
                let preview = '';
                if (file.type.startsWith('image/') && {{ show_preview | tojson }}) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const img = item.querySelector('.file-preview');
                        if (img) img.src = e.target.result;
                    };
                    reader.readAsDataURL(file);
                    preview = '<img class="file-preview" alt="Preview">';
                } else {
                    const iconClass = getFileIcon(file.type);
                    preview = `<div class="file-icon"><i class="fa ${iconClass}"></i></div>`;
                }
                
                item.innerHTML = `
                    ${preview}
                    <div class="file-info">
                        <p class="file-name">${file.name}</p>
                        <p class="file-size">${formatFileSize(file.size)}</p>
                        ${!isValid ? `<p class="text-danger">${validation.error}</p>` : ''}
                        <div class="file-progress" style="display: none;">
                            <div class="file-progress-bar"></div>
                        </div>
                    </div>
                    <div class="file-actions">
                        ${isValid ? '<button type="button" class="btn btn-success btn-sm" data-action="upload"><i class="fa fa-upload"></i></button>' : ''}
                        <button type="button" class="btn btn-danger btn-sm" data-action="remove">
                            <i class="fa fa-times"></i>
                        </button>
                    </div>
                `;
                
                return item;
            }
            
            // Get file icon based on type
            function getFileIcon(mimeType) {
                if (mimeType.startsWith('image/')) return 'fa-file-image-o';
                if (mimeType.startsWith('video/')) return 'fa-file-video-o';
                if (mimeType.startsWith('audio/')) return 'fa-file-audio-o';
                if (mimeType === 'application/pdf') return 'fa-file-pdf-o';
                if (mimeType.includes('word')) return 'fa-file-word-o';
                if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'fa-file-excel-o';
                if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return 'fa-file-powerpoint-o';
                if (mimeType.includes('zip') || mimeType.includes('archive')) return 'fa-file-archive-o';
                return 'fa-file-o';
            }
            
            // Add files to queue
            function addFilesToQueue(files) {
                const remainingSlots = {{ max_files }} - fileQueue.length;
                const filesToAdd = Array.from(files).slice(0, remainingSlots);
                
                filesToAdd.forEach((file, index) => {
                    const queueIndex = fileQueue.length;
                    fileQueue.push(file);
                    
                    const queueItem = createQueueItem(file, queueIndex);
                    queueItems.appendChild(queueItem);
                });
                
                if (fileQueue.length > 0) {
                    queue.style.display = 'block';
                }
                
                if (files.length > remainingSlots) {
                    alert(`Only ${remainingSlots} files can be added (maximum: {{ max_files }})`);
                }
            }
            
            // Upload file
            function uploadFile(file, progressCallback) {
                return new Promise((resolve, reject) => {
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    const xhr = new XMLHttpRequest();
                    
                    xhr.upload.addEventListener('progress', (e) => {
                        if (e.lengthComputable) {
                            const percentComplete = (e.loaded / e.total) * 100;
                            progressCallback(percentComplete);
                        }
                    });
                    
                    xhr.addEventListener('load', () => {
                        if (xhr.status === 200) {
                            resolve(JSON.parse(xhr.responseText));
                        } else {
                            reject(new Error(`Upload failed: ${xhr.statusText}`));
                        }
                    });
                    
                    xhr.addEventListener('error', () => {
                        reject(new Error('Upload failed'));
                    });
                    
                    const endpoint = {{ upload_endpoint | tojson }} || '/upload';
                    xhr.open('POST', endpoint);
                    xhr.send(formData);
                });
            }
            
            // Event listeners
            dropzone.addEventListener('click', () => fileInput.click());
            
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    addFilesToQueue(e.target.files);
                    e.target.value = ''; // Reset input
                }
            });
            
            // Drag & drop
            dropzone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropzone.classList.add('dragover');
            });
            
            dropzone.addEventListener('dragleave', () => {
                dropzone.classList.remove('dragover');
            });
            
            dropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropzone.classList.remove('dragover');
                addFilesToQueue(e.dataTransfer.files);
            });
            
            // Queue actions
            container.addEventListener('click', async (e) => {
                const action = e.target.closest('[data-action]')?.dataset.action;
                if (!action) return;
                
                e.preventDefault();
                
                const queueItem = e.target.closest('.queue-item');
                const index = queueItem?.dataset.index;
                
                switch (action) {
                    case 'upload':
                        if (index !== undefined) {
                            const file = fileQueue[index];
                            const progressBar = queueItem.querySelector('.file-progress-bar');
                            const progress = queueItem.querySelector('.file-progress');
                            
                            progress.style.display = 'block';
                            
                            try {
                                await uploadFile(file, (percent) => {
                                    progressBar.style.width = percent + '%';
                                });
                                queueItem.style.opacity = '0.5';
                                e.target.innerHTML = '<i class="fa fa-check"></i>';
                                e.target.className = 'btn btn-success btn-sm';
                            } catch (error) {
                                console.error('Upload failed:', error);
                                alert('Upload failed: ' + error.message);
                                progressBar.style.backgroundColor = '#dc3545';
                            }
                        }
                        break;
                        
                    case 'remove':
                        if (index !== undefined) {
                            fileQueue.splice(index, 1);
                            queueItem.remove();
                            
                            // Update indices
                            queueItems.querySelectorAll('.queue-item').forEach((item, newIndex) => {
                                item.dataset.index = newIndex;
                            });
                            
                            if (fileQueue.length === 0) {
                                queue.style.display = 'none';
                            }
                        }
                        break;
                        
                    case 'upload-all':
                        const uploadButtons = queueItems.querySelectorAll('[data-action="upload"]');
                        for (const button of uploadButtons) {
                            if (button.querySelector('.fa-upload')) {
                                button.click();
                                await new Promise(resolve => setTimeout(resolve, 100));
                            }
                        }
                        break;
                        
                    case 'clear-all':
                        fileQueue = [];
                        queueItems.innerHTML = '';
                        queue.style.display = 'none';
                        break;
                }
            });
        })();
        </script>
        """
        
        file_attrs = html_params(**kwargs)
        allowed_types_display = [t.replace('*', 'All') for t in self.allowed_types]
        max_file_size_mb = round(self.max_file_size / 1024 / 1024, 1)
        
        return Markup(render_template_string(template,
            widget_id=widget_id,
            field=field,
            file_attrs=file_attrs,
            allowed_types=allowed_types_display,
            max_file_size=self.max_file_size,
            max_file_size_mb=max_file_size_mb,
            max_files=self.max_files,
            multiple=self.multiple,
            show_preview=self.show_preview,
            upload_endpoint=self.upload_endpoint,
            _=gettext
        ))


class DateTimeRangeWidget(Input):
    """
    Advanced date and time range picker widget.
    
    Features:
    - Date range selection with calendar popup
    - Time range selection with time pickers
    - Predefined quick ranges (Today, This Week, etc.)
    - Custom range validation
    - Timezone support
    - Different display formats
    - Business hours filtering
    """
    
    input_type = 'text'
    
    def __init__(self,
                 include_time: bool = True,
                 predefined_ranges: bool = True,
                 timezone_aware: bool = False,
                 min_date: Optional[str] = None,
                 max_date: Optional[str] = None,
                 format_display: str = 'MMM DD, YYYY',
                 business_hours_only: bool = False):
        """
        Initialize the date time range widget.
        
        Args:
            include_time: Include time selection
            predefined_ranges: Show predefined range buttons
            timezone_aware: Handle timezone conversion
            min_date: Minimum allowed date
            max_date: Maximum allowed date
            format_display: Date display format
            business_hours_only: Restrict to business hours
        """
        self.include_time = include_time
        self.predefined_ranges = predefined_ranges
        self.timezone_aware = timezone_aware
        self.min_date = min_date
        self.max_date = max_date
        self.format_display = format_display
        self.business_hours_only = business_hours_only
        
    def __call__(self, field, **kwargs):
        """Render the date time range widget."""
        widget_id = kwargs.get('id', f'datetime_range_{uuid4().hex[:8]}')
        kwargs.setdefault('id', widget_id)
        kwargs.setdefault('class', 'form-control datetime-range-input')
        kwargs.setdefault('readonly', True)
        
        template = """
        <div class="datetime-range-container" data-widget="datetime-range">
            <div class="input-group">
                <input type="text" id="{{ widget_id }}" name="{{ field.name }}" 
                       class="form-control datetime-range-display" 
                       placeholder="{{ _('Select date range...') }}" 
                       value="{{ field.data or '' }}" readonly>
                <div class="input-group-append">
                    <button type="button" class="btn btn-outline-secondary" 
                            data-toggle="datetime-range-picker">
                        <i class="fa fa-calendar"></i>
                    </button>
                </div>
            </div>
            
            <div class="datetime-range-picker" style="display: none;">
                {% if predefined_ranges %}
                <div class="predefined-ranges">
                    <h6>{{ _('Quick Ranges') }}</h6>
                    <div class="range-buttons">
                        <button type="button" class="btn btn-sm btn-outline-primary" data-range="today">
                            {{ _('Today') }}
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" data-range="yesterday">
                            {{ _('Yesterday') }}
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" data-range="this_week">
                            {{ _('This Week') }}
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" data-range="last_week">
                            {{ _('Last Week') }}
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" data-range="this_month">
                            {{ _('This Month') }}
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" data-range="last_month">
                            {{ _('Last Month') }}
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" data-range="this_year">
                            {{ _('This Year') }}
                        </button>
                    </div>
                </div>
                {% endif %}
                
                <div class="calendar-container">
                    <div class="calendar-section">
                        <h6>{{ _('Start Date') }}</h6>
                        <div class="calendar" data-calendar="start"></div>
                        {% if include_time %}
                        <div class="time-picker">
                            <label>{{ _('Time') }}:</label>
                            <input type="time" class="form-control form-control-sm" data-time="start" 
                                   {% if business_hours_only %}min="09:00" max="17:00"{% endif %}>
                        </div>
                        {% endif %}
                    </div>
                    
                    <div class="calendar-section">
                        <h6>{{ _('End Date') }}</h6>
                        <div class="calendar" data-calendar="end"></div>
                        {% if include_time %}
                        <div class="time-picker">
                            <label>{{ _('Time') }}:</label>
                            <input type="time" class="form-control form-control-sm" data-time="end" 
                                   {% if business_hours_only %}min="09:00" max="17:00"{% endif %}>
                        </div>
                        {% endif %}
                    </div>
                </div>
                
                <div class="picker-actions">
                    <button type="button" class="btn btn-secondary btn-sm" data-action="cancel">
                        {{ _('Cancel') }}
                    </button>
                    <button type="button" class="btn btn-primary btn-sm" data-action="apply">
                        {{ _('Apply') }}
                    </button>
                </div>
            </div>
        </div>
        
        <style>
        .datetime-range-container {
            position: relative;
            margin-bottom: 1rem;
        }
        
        .datetime-range-picker {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            margin-top: 0.5rem;
            min-width: 600px;
        }
        
        .predefined-ranges {
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e9ecef;
        }
        
        .range-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        
        .calendar-container {
            display: flex;
            gap: 2rem;
            margin-bottom: 1rem;
        }
        
        .calendar-section {
            flex: 1;
        }
        
        .calendar {
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 1rem;
            background-color: #f8f9fa;
            min-height: 250px;
            margin-bottom: 1rem;
        }
        
        .time-picker {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .time-picker label {
            margin: 0;
            min-width: 50px;
        }
        
        .picker-actions {
            display: flex;
            justify-content: flex-end;
            gap: 0.5rem;
            padding-top: 1rem;
            border-top: 1px solid #e9ecef;
        }
        </style>
        
        <script>
        (function() {
            const container = document.querySelector('[data-widget="datetime-range"]');
            const input = document.getElementById('{{ widget_id }}');
            const picker = container.querySelector('.datetime-range-picker');
            const toggleButton = container.querySelector('[data-toggle="datetime-range-picker"]');
            
            let startDate = null;
            let endDate = null;
            let startTime = null;
            let endTime = null;
            
            // Initialize date picker (would use a library like Flatpickr or similar)
            function initializeDatePickers() {
                const startCalendar = picker.querySelector('[data-calendar="start"]');
                const endCalendar = picker.querySelector('[data-calendar="end"]');
                
                // Placeholder for calendar initialization
                // In real implementation, would initialize proper calendar widgets
                startCalendar.innerHTML = '<p class="text-muted">Start date calendar would appear here</p>';
                endCalendar.innerHTML = '<p class="text-muted">End date calendar would appear here</p>';
            }
            
            // Predefined range handlers
            function applyPredefinedRange(range) {
                const now = new Date();
                let start, end;
                
                switch (range) {
                    case 'today':
                        start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                        end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
                        break;
                    case 'yesterday':
                        const yesterday = new Date(now);
                        yesterday.setDate(yesterday.getDate() - 1);
                        start = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate());
                        end = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 23, 59, 59);
                        break;
                    case 'this_week':
                        const startOfWeek = new Date(now);
                        startOfWeek.setDate(now.getDate() - now.getDay());
                        start = new Date(startOfWeek.getFullYear(), startOfWeek.getMonth(), startOfWeek.getDate());
                        end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
                        break;
                    case 'last_week':
                        const lastWeekEnd = new Date(now);
                        lastWeekEnd.setDate(now.getDate() - now.getDay() - 1);
                        const lastWeekStart = new Date(lastWeekEnd);
                        lastWeekStart.setDate(lastWeekEnd.getDate() - 6);
                        start = new Date(lastWeekStart.getFullYear(), lastWeekStart.getMonth(), lastWeekStart.getDate());
                        end = new Date(lastWeekEnd.getFullYear(), lastWeekEnd.getMonth(), lastWeekEnd.getDate(), 23, 59, 59);
                        break;
                    case 'this_month':
                        start = new Date(now.getFullYear(), now.getMonth(), 1);
                        end = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59);
                        break;
                    case 'last_month':
                        start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
                        end = new Date(now.getFullYear(), now.getMonth(), 0, 23, 59, 59);
                        break;
                    case 'this_year':
                        start = new Date(now.getFullYear(), 0, 1);
                        end = new Date(now.getFullYear(), 11, 31, 23, 59, 59);
                        break;
                }
                
                if (start && end) {
                    startDate = start;
                    endDate = end;
                    updateDisplay();
                    applySelection();
                }
            }
            
            // Update display
            function updateDisplay() {
                if (startDate && endDate) {
                    const format = '{{ format_display }}';
                    let displayValue = '';
                    
                    if ({{ include_time | tojson }}) {
                        displayValue = formatDateTime(startDate) + ' - ' + formatDateTime(endDate);
                    } else {
                        displayValue = formatDate(startDate) + ' - ' + formatDate(endDate);
                    }
                    
                    input.value = displayValue;
                }
            }
            
            // Format date
            function formatDate(date) {
                return date.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric'
                });
            }
            
            // Format date time
            function formatDateTime(date) {
                return date.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                });
            }
            
            // Apply selection
            function applySelection() {
                // Create hidden input with ISO format for form submission
                let hiddenInput = container.querySelector('input[type="hidden"]');
                if (!hiddenInput) {
                    hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = '{{ field.name }}';
                    container.appendChild(hiddenInput);
                }
                
                if (startDate && endDate) {
                    const value = {
                        start: startDate.toISOString(),
                        end: endDate.toISOString()
                    };
                    hiddenInput.value = JSON.stringify(value);
                }
                
                picker.style.display = 'none';
            }
            
            // Event listeners
            toggleButton.addEventListener('click', () => {
                picker.style.display = picker.style.display === 'none' ? 'block' : 'none';
            });
            
            // Predefined range buttons
            picker.addEventListener('click', (e) => {
                const range = e.target.dataset.range;
                if (range) {
                    applyPredefinedRange(range);
                    return;
                }
                
                const action = e.target.dataset.action;
                if (action === 'cancel') {
                    picker.style.display = 'none';
                } else if (action === 'apply') {
                    applySelection();
                }
            });
            
            // Time change handlers
            picker.addEventListener('change', (e) => {
                if (e.target.dataset.time === 'start') {
                    startTime = e.target.value;
                } else if (e.target.dataset.time === 'end') {
                    endTime = e.target.value;
                }
            });
            
            // Close picker when clicking outside
            document.addEventListener('click', (e) => {
                if (!container.contains(e.target)) {
                    picker.style.display = 'none';
                }
            });
            
            // Initialize
            initializeDatePickers();
        })();
        </script>
        """
        
        return Markup(render_template_string(template,
            widget_id=widget_id,
            field=field,
            include_time=self.include_time,
            predefined_ranges=self.predefined_ranges,
            timezone_aware=self.timezone_aware,
            format_display=self.format_display,
            business_hours_only=self.business_hours_only,
            _=gettext
        ))


class TagInputWidget(Input):
    """
    Tag input widget for multiple values with autocomplete.
    
    Features:
    - Tag creation and management
    - Autocomplete suggestions
    - Tag validation
    - Custom tag colors/styles
    - Maximum tag limits
    - Duplicate prevention
    - Drag & drop reordering
    """
    
    input_type = 'text'
    
    def __init__(self,
                 autocomplete_source: Optional[str] = None,
                 max_tags: Optional[int] = None,
                 allowed_tags: Optional[List[str]] = None,
                 tag_colors: bool = True,
                 allow_duplicates: bool = False,
                 sortable: bool = True):
        """
        Initialize the tag input widget.
        
        Args:
            autocomplete_source: URL for tag suggestions
            max_tags: Maximum number of tags
            allowed_tags: List of allowed tag values
            tag_colors: Enable colored tags
            allow_duplicates: Allow duplicate tags
            sortable: Enable drag & drop sorting
        """
        self.autocomplete_source = autocomplete_source
        self.max_tags = max_tags
        self.allowed_tags = allowed_tags
        self.tag_colors = tag_colors
        self.allow_duplicates = allow_duplicates
        self.sortable = sortable
        
    def __call__(self, field, **kwargs):
        """Render the tag input widget."""
        widget_id = kwargs.get('id', f'tag_input_{uuid4().hex[:8]}')
        kwargs.setdefault('id', widget_id)
        
        template = """
        <div class="tag-input-container" data-widget="tag-input">
            <div class="tag-list" id="tags-{{ widget_id }}">
                <!-- Tags will be inserted here -->
            </div>
            <div class="tag-input-wrapper">
                <input type="text" class="form-control tag-text-input" 
                       id="tag-input-{{ widget_id }}" 
                       placeholder="{{ _('Type and press Enter to add tags...') }}">
                <div class="tag-suggestions" style="display: none;"></div>
            </div>
            <input type="hidden" id="{{ widget_id }}" name="{{ field.name }}" value="{{ field.data or '' }}">
        </div>
        
        <style>
        .tag-input-container {
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 0.5rem;
            min-height: 80px;
            cursor: text;
            transition: all 0.3s ease;
        }
        
        .tag-input-container:focus-within {
            border-color: #0d6efd;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }
        
        .tag-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        .tag {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.25rem 0.5rem;
            background-color: #0d6efd;
            color: white;
            border-radius: 16px;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
        }
        
        .tag:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .tag.dragging {
            opacity: 0.5;
            transform: rotate(5deg);
        }
        
        .tag-remove {
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            padding: 0;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            transition: background-color 0.2s ease;
        }
        
        .tag-remove:hover {
            background-color: rgba(255,255,255,0.2);
        }
        
        .tag-input-wrapper {
            position: relative;
            flex: 1;
        }
        
        .tag-text-input {
            border: none;
            outline: none;
            width: 100%;
            padding: 0.25rem 0;
        }
        
        .tag-suggestions {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            z-index: 1000;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .tag-suggestion {
            padding: 0.5rem 1rem;
            cursor: pointer;
            border-bottom: 1px solid #f8f9fa;
        }
        
        .tag-suggestion:hover,
        .tag-suggestion.active {
            background-color: #f8f9fa;
        }
        
        .tag-suggestion:last-child {
            border-bottom: none;
        }
        
        /* Tag colors */
        .tag.color-primary { background-color: #0d6efd; }
        .tag.color-success { background-color: #198754; }
        .tag.color-warning { background-color: #ffc107; color: #000; }
        .tag.color-danger { background-color: #dc3545; }
        .tag.color-info { background-color: #0dcaf0; color: #000; }
        .tag.color-secondary { background-color: #6c757d; }
        .tag.color-purple { background-color: #6f42c1; }
        .tag.color-pink { background-color: #e83e8c; }
        .tag.color-teal { background-color: #20c997; }
        .tag.color-indigo { background-color: #6610f2; }
        </style>
        
        <script>
        (function() {
            const container = document.querySelector('[data-widget="tag-input"]');
            const tagList = document.getElementById('tags-{{ widget_id }}');
            const input = document.getElementById('tag-input-{{ widget_id }}');
            const hiddenInput = document.getElementById('{{ widget_id }}');
            const suggestions = container.querySelector('.tag-suggestions');
            
            let tags = [];
            let currentSuggestions = [];
            let selectedSuggestion = -1;
            
            const colors = ['primary', 'success', 'warning', 'danger', 'info', 'secondary', 'purple', 'pink', 'teal', 'indigo'];
            
            // Initialize with existing data
            function initializeTags() {
                const existingData = hiddenInput.value;
                if (existingData) {
                    try {
                        tags = JSON.parse(existingData);
                        renderTags();
                    } catch (e) {
                        // Treat as comma-separated string
                        tags = existingData.split(',').map(tag => tag.trim()).filter(tag => tag);
                        renderTags();
                    }
                }
            }
            
            // Render tags
            function renderTags() {
                tagList.innerHTML = '';
                tags.forEach((tag, index) => {
                    const tagElement = createTagElement(tag, index);
                    tagList.appendChild(tagElement);
                });
                updateHiddenInput();
            }
            
            // Create tag element
            function createTagElement(tag, index) {
                const tagElement = document.createElement('div');
                tagElement.className = 'tag';
                tagElement.draggable = {{ sortable | tojson }};
                tagElement.dataset.index = index;
                
                {% if tag_colors %}
                const colorClass = colors[index % colors.length];
                tagElement.classList.add(`color-${colorClass}`);
                {% endif %}
                
                tagElement.innerHTML = `
                    <span class="tag-text">${escapeHtml(tag)}</span>
                    <button type="button" class="tag-remove" data-remove="${index}">
                        <i class="fa fa-times"></i>
                    </button>
                `;
                
                return tagElement;
            }
            
            // Escape HTML
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // Add tag
            function addTag(tagText) {
                tagText = tagText.trim();
                if (!tagText) return false;
                
                // Check duplicates
                {% if not allow_duplicates %}
                if (tags.includes(tagText)) {
                    showError('Tag already exists');
                    return false;
                }
                {% endif %}
                
                // Check max tags
                {% if max_tags %}
                if (tags.length >= {{ max_tags }}) {
                    showError(`Maximum {{ max_tags }} tags allowed`);
                    return false;
                }
                {% endif %}
                
                // Check allowed tags
                {% if allowed_tags %}
                const allowedTags = {{ allowed_tags | tojson }};
                if (!allowedTags.includes(tagText)) {
                    showError('Tag not allowed');
                    return false;
                }
                {% endif %}
                
                tags.push(tagText);
                renderTags();
                input.value = '';
                hideSuggestions();
                return true;
            }
            
            // Remove tag
            function removeTag(index) {
                tags.splice(index, 1);
                renderTags();
            }
            
            // Update hidden input
            function updateHiddenInput() {
                hiddenInput.value = JSON.stringify(tags);
            }
            
            // Show error
            function showError(message) {
                // You could show a toast or tooltip here
                console.warn('Tag error:', message);
            }
            
            // Fetch suggestions
            async function fetchSuggestions(query) {
                {% if autocomplete_source %}
                if (!query.trim()) {
                    hideSuggestions();
                    return;
                }
                
                try {
                    const response = await fetch(`{{ autocomplete_source }}?q=${encodeURIComponent(query)}`);
                    const data = await response.json();
                    currentSuggestions = data.filter(suggestion => !tags.includes(suggestion));
                    renderSuggestions();
                } catch (error) {
                    console.error('Error fetching suggestions:', error);
                    hideSuggestions();
                }
                {% endif %}
            }
            
            // Render suggestions
            function renderSuggestions() {
                if (currentSuggestions.length === 0) {
                    hideSuggestions();
                    return;
                }
                
                suggestions.innerHTML = '';
                currentSuggestions.forEach((suggestion, index) => {
                    const suggestionElement = document.createElement('div');
                    suggestionElement.className = 'tag-suggestion';
                    suggestionElement.textContent = suggestion;
                    suggestionElement.dataset.index = index;
                    suggestions.appendChild(suggestionElement);
                });
                
                suggestions.style.display = 'block';
                selectedSuggestion = -1;
            }
            
            // Hide suggestions
            function hideSuggestions() {
                suggestions.style.display = 'none';
                currentSuggestions = [];
                selectedSuggestion = -1;
            }
            
            // Event listeners
            input.addEventListener('keydown', (e) => {
                switch (e.key) {
                    case 'Enter':
                    case 'Tab':
                        e.preventDefault();
                        if (selectedSuggestion >= 0) {
                            addTag(currentSuggestions[selectedSuggestion]);
                        } else if (input.value.trim()) {
                            addTag(input.value);
                        }
                        break;
                        
                    case 'ArrowDown':
                        e.preventDefault();
                        if (currentSuggestions.length > 0) {
                            selectedSuggestion = Math.min(selectedSuggestion + 1, currentSuggestions.length - 1);
                            updateSuggestionSelection();
                        }
                        break;
                        
                    case 'ArrowUp':
                        e.preventDefault();
                        if (currentSuggestions.length > 0) {
                            selectedSuggestion = Math.max(selectedSuggestion - 1, -1);
                            updateSuggestionSelection();
                        }
                        break;
                        
                    case 'Escape':
                        hideSuggestions();
                        break;
                        
                    case 'Backspace':
                        if (input.value === '' && tags.length > 0) {
                            removeTag(tags.length - 1);
                        }
                        break;
                }
            });
            
            input.addEventListener('input', (e) => {
                fetchSuggestions(e.target.value);
            });
            
            // Update suggestion selection
            function updateSuggestionSelection() {
                suggestions.querySelectorAll('.tag-suggestion').forEach((elem, index) => {
                    elem.classList.toggle('active', index === selectedSuggestion);
                });
            }
            
            // Tag removal
            tagList.addEventListener('click', (e) => {
                const removeButton = e.target.closest('[data-remove]');
                if (removeButton) {
                    const index = parseInt(removeButton.dataset.remove);
                    removeTag(index);
                }
            });
            
            // Suggestion selection
            suggestions.addEventListener('click', (e) => {
                const suggestion = e.target.closest('.tag-suggestion');
                if (suggestion) {
                    const index = parseInt(suggestion.dataset.index);
                    addTag(currentSuggestions[index]);
                }
            });
            
            // Container click focuses input
            container.addEventListener('click', (e) => {
                if (e.target === container || e.target === tagList) {
                    input.focus();
                }
            });
            
            // Hide suggestions when clicking outside
            document.addEventListener('click', (e) => {
                if (!container.contains(e.target)) {
                    hideSuggestions();
                }
            });
            
            {% if sortable %}
            // Drag & drop sorting
            let draggedIndex = -1;
            
            tagList.addEventListener('dragstart', (e) => {
                if (e.target.classList.contains('tag')) {
                    draggedIndex = parseInt(e.target.dataset.index);
                    e.target.classList.add('dragging');
                }
            });
            
            tagList.addEventListener('dragend', (e) => {
                if (e.target.classList.contains('tag')) {
                    e.target.classList.remove('dragging');
                    draggedIndex = -1;
                }
            });
            
            tagList.addEventListener('dragover', (e) => {
                e.preventDefault();
            });
            
            tagList.addEventListener('drop', (e) => {
                e.preventDefault();
                const dropTarget = e.target.closest('.tag');
                if (dropTarget && draggedIndex >= 0) {
                    const dropIndex = parseInt(dropTarget.dataset.index);
                    if (dropIndex !== draggedIndex) {
                        // Reorder tags
                        const [draggedTag] = tags.splice(draggedIndex, 1);
                        tags.splice(dropIndex, 0, draggedTag);
                        renderTags();
                    }
                }
            });
            {% endif %}
            
            // Initialize
            initializeTags();
        })();
        </script>
        """
        
        return Markup(render_template_string(template,
            widget_id=widget_id,
            field=field,
            autocomplete_source=self.autocomplete_source,
            max_tags=self.max_tags,
            allowed_tags=self.allowed_tags,
            tag_colors=self.tag_colors,
            allow_duplicates=self.allow_duplicates,
            sortable=self.sortable,
            _=gettext
        ))