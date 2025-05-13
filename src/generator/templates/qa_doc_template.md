# QA Test Documentation: {{ source_url }}
**Analysis Date:** {{ analysis_timestamp }}

## Page: {{ page_title }}

{% if test_cases.functional %}
## Functional Test Cases
{% for test_case in test_cases.functional %}
### Test Case ID: {{ test_case.test_case_id }}
* **Title:** {{ test_case.test_case_title }}
* **Type:** Functional
* **Priority:** {{ test_case.priority|capitalize }}
* **Description:** {{ test_case.description }}
{% if test_case.element_details %}
* **Related Element:** `{{ test_case.element_details.selector }}`{% if test_case.element_details.visible_text %} (Text: "{{ test_case.element_details.visible_text|truncate(30) }}"){% endif %}
{% endif %}
{% if test_case.preconditions %}
* **Preconditions:**
{% for precondition in test_case.preconditions %}
    * {{ precondition }}
{% endfor %}
{% endif %}
* **Steps:**
{% for step in test_case.steps %}
    {{ step.step_number }}. **Action:** {{ step.action }}
       **Expected Result:** {{ step.expected_result }}
{% endfor %}

{% endfor %}
{% endif %}

{% if test_cases.usability %}
## Usability Test Cases
{% for test_case in test_cases.usability %}
### Test Case ID: {{ test_case.test_case_id }}
* **Title:** {{ test_case.test_case_title }}
* **Type:** Usability
* **Priority:** {{ test_case.priority|capitalize }}
* **Description:** {{ test_case.description }}
{% if test_case.element_details %}
* **Related Element:** `{{ test_case.element_details.selector }}`{% if test_case.element_details.visible_text %} (Text: "{{ test_case.element_details.visible_text|truncate(30) }}"){% endif %}
{% endif %}
{% if test_case.preconditions %}
* **Preconditions:**
{% for precondition in test_case.preconditions %}
    * {{ precondition }}
{% endfor %}
{% endif %}
* **Steps:**
{% for step in test_case.steps %}
    {{ step.step_number }}. **Action:** {{ step.action }}
       **Expected Result:** {{ step.expected_result }}
{% endfor %}

{% endfor %}
{% endif %}

{% if test_cases.edge_case %}
## Edge Case Test Cases
{% for test_case in test_cases.edge_case %}
### Test Case ID: {{ test_case.test_case_id }}
* **Title:** {{ test_case.test_case_title }}
* **Type:** Edge Case
* **Priority:** {{ test_case.priority|capitalize }}
* **Description:** {{ test_case.description }}
{% if test_case.element_details %}
* **Related Element:** `{{ test_case.element_details.selector }}`{% if test_case.element_details.visible_text %} (Text: "{{ test_case.element_details.visible_text|truncate(30) }}"){% endif %}
{% endif %}
{% if test_case.preconditions %}
* **Preconditions:**
{% for precondition in test_case.preconditions %}
    * {{ precondition }}
{% endfor %}
{% endif %}
* **Steps:**
{% for step in test_case.steps %}
    {{ step.step_number }}. **Action:** {{ step.action }}
       **Expected Result:** {{ step.expected_result }}
{% endfor %}

{% endfor %}
{% endif %}

{% if test_cases.accessibility_check %}
## Accessibility Test Cases
{% for test_case in test_cases.accessibility_check %}
### Test Case ID: {{ test_case.test_case_id }}
* **Title:** {{ test_case.test_case_title }}
* **Type:** Accessibility Check
* **Priority:** {{ test_case.priority|capitalize }}
* **Description:** {{ test_case.description }}
{% if test_case.element_details %}
* **Related Element:** `{{ test_case.element_details.selector }}`{% if test_case.element_details.visible_text %} (Text: "{{ test_case.element_details.visible_text|truncate(30) }}"){% endif %}
{% endif %}
{% if test_case.preconditions %}
* **Preconditions:**
{% for precondition in test_case.preconditions %}
    * {{ precondition }}
{% endfor %}
{% endif %}
* **Steps:**
{% for step in test_case.steps %}
    {{ step.step_number }}. **Action:** {{ step.action }}
       **Expected Result:** {{ step.expected_result }}
{% endfor %}

{% endfor %}
{% endif %} 