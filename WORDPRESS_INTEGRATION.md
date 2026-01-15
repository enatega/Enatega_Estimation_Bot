# WordPress Integration Guide - Estimation Bot API

## Overview

This guide helps frontend developers integrate the Estimation Bot API into WordPress. The API provides time and cost estimates for client onboarding features based on requirements provided as text or file uploads.

## API Base URL

```
Production: https://your-railway-app.railway.app
Local Development: http://localhost:8000
```

**Note:** All API endpoints are prefixed with `/api/v1`

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /api/v1/health`

**Description:** Check if the API is running

**Response:**
```json
{
  "status": "healthy",
  "service": "Estimation Bot API",
  "version": "1.0.0"
}
```

---

### 2. Generate Estimate

**Endpoint:** `POST /api/v1/estimate`

**Description:** Generate time and cost estimates based on requirements

**Content-Type:** `multipart/form-data`

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `requirements` | string | No* | Text description of requirements (required if no file provided) |
| `file` | file | No* | PDF, DOCX, DOC, or TXT file with requirements (required if no text provided) |
| `hourly_rate` | float | No | Custom hourly rate (default: $30/hour) |

*Note: Either `requirements` or `file` (or both) must be provided. Supported file types: PDF, DOCX, DOC, TXT.*

#### Request Examples

**Text Only:**
```javascript
const formData = new FormData();
formData.append('requirements', 'I want to add HYP payment method in enatega');
formData.append('hourly_rate', '30');
```

**File Only:**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]); // PDF, DOCX, DOC, or TXT file
formData.append('hourly_rate', '30');
```

**Text + File:**
```javascript
const formData = new FormData();
formData.append('requirements', 'Payment integration with HYP gateway');
formData.append('file', fileInput.files[0]);
formData.append('hourly_rate', '30');
```

#### Response Format

**Success Response (200 OK):**
```json
{
  "estimated_time_hours_min": 38.0,
  "estimated_time_hours_max": 42.0,
  "estimated_cost_min": 1140.00,
  "estimated_cost_max": 1260.00
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "Could not extract features from requirements. Please provide more specific details about the features you need."
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "detail": "Error generating estimate: [error message]"
}
```

---

## WordPress Integration

### Method 1: Using WordPress HTTP API (Recommended)

Add this to your WordPress theme's `functions.php` or a custom plugin:

```php
<?php
/**
 * Estimation Bot API Integration for WordPress
 */

class EstimationBotAPI {
    private $api_base_url = 'https://your-railway-app.railway.app/api/v1';
    
    /**
     * Get estimate from API
     * 
     * @param string $requirements Text requirements
     * @param string $file_path Path to uploaded file (optional)
     * @param float $hourly_rate Custom hourly rate (optional, default: 30)
     * @return array|WP_Error Response data or error
     */
    public function get_estimate($requirements = '', $file_path = '', $hourly_rate = 30) {
        $url = $this->api_base_url . '/estimate';
        
        // Prepare multipart form data
        $boundary = wp_generate_password(12, false);
        $body = '';
        
        // Add requirements if provided
        if (!empty($requirements)) {
            $body .= '--' . $boundary . "\r\n";
            $body .= 'Content-Disposition: form-data; name="requirements"' . "\r\n\r\n";
            $body .= $requirements . "\r\n";
        }
        
        // Add file if provided
        if (!empty($file_path) && file_exists($file_path)) {
            $file_content = file_get_contents($file_path);
            $file_name = basename($file_path);
            $file_type = wp_check_filetype($file_name)['type'];
            
            $body .= '--' . $boundary . "\r\n";
            $body .= 'Content-Disposition: form-data; name="file"; filename="' . $file_name . '"' . "\r\n";
            $body .= 'Content-Type: ' . $file_type . "\r\n\r\n";
            $body .= $file_content . "\r\n";
        }
        
        // Add hourly rate
        $body .= '--' . $boundary . "\r\n";
        $body .= 'Content-Disposition: form-data; name="hourly_rate"' . "\r\n\r\n";
        $body .= $hourly_rate . "\r\n";
        $body .= '--' . $boundary . '--';
        
        // Make request
        $response = wp_remote_post($url, array(
            'headers' => array(
                'Content-Type' => 'multipart/form-data; boundary=' . $boundary,
            ),
            'body' => $body,
            'timeout' => 60,
        ));
        
        if (is_wp_error($response)) {
            return $response;
        }
        
        $response_code = wp_remote_retrieve_response_code($response);
        $response_body = wp_remote_retrieve_body($response);
        $data = json_decode($response_body, true);
        
        if ($response_code === 200) {
            return $data;
        } else {
            return new WP_Error('api_error', $data['detail'] ?? 'Unknown error', array('status' => $response_code));
        }
    }
    
    /**
     * Check API health
     */
    public function check_health() {
        $url = $this->api_base_url . '/health';
        $response = wp_remote_get($url, array('timeout' => 10));
        
        if (is_wp_error($response)) {
            return false;
        }
        
        $response_code = wp_remote_retrieve_response_code($response);
        return $response_code === 200;
    }
}

// Initialize
$estimation_bot = new EstimationBotAPI();
```

### Method 2: Using cURL (Alternative)

```php
function get_estimate_curl($requirements, $file_path = '', $hourly_rate = 30) {
    $url = 'https://your-railway-app.railway.app/api/v1/estimate';
    
    $ch = curl_init();
    
    $post_fields = array(
        'requirements' => $requirements,
        'hourly_rate' => $hourly_rate
    );
    
    // Add file if provided
    if (!empty($file_path) && file_exists($file_path)) {
        $post_fields['file'] = new CURLFile($file_path);
    }
    
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $post_fields);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($http_code === 200) {
        return json_decode($response, true);
    } else {
        $error = json_decode($response, true);
        return array('error' => $error['detail'] ?? 'Unknown error');
    }
}
```

---

## WordPress Shortcode Example

Create a shortcode to display estimation form:

```php
/**
 * Shortcode: [estimation_form]
 */
function estimation_form_shortcode($atts) {
    $atts = shortcode_atts(array(
        'api_url' => 'https://your-railway-app.railway.app/api/v1',
    ), $atts);
    
    ob_start();
    ?>
    <div class="estimation-form-container">
        <form id="estimation-form" method="post">
            <div class="form-group">
                <label for="requirements">Requirements:</label>
                <textarea id="requirements" name="requirements" rows="5" required></textarea>
            </div>
            
            <div class="form-group">
                <label for="estimate_file">Upload File (PDF/DOCX/DOC/TXT):</label>
                <input type="file" id="estimate_file" name="file" accept=".pdf,.docx,.doc,.txt">
            </div>
            
            <div class="form-group">
                <label for="hourly_rate">Hourly Rate (optional):</label>
                <input type="number" id="hourly_rate" name="hourly_rate" value="30" step="0.01">
            </div>
            
            <button type="submit">Get Estimate</button>
        </form>
        
        <div id="estimate-result" style="display:none;">
            <h3>Estimate Result</h3>
            <div class="estimate-time">
                <strong>Estimated Time:</strong> <span id="time-min"></span> - <span id="time-max"></span> hours
            </div>
            <div class="estimate-cost">
                <strong>Estimated Cost:</strong> $<span id="cost-min"></span> - $<span id="cost-max"></span>
            </div>
        </div>
    </div>
    
    <script>
    jQuery(document).ready(function($) {
        $('#estimation-form').on('submit', function(e) {
            e.preventDefault();
            
            var formData = new FormData();
            var requirements = $('#requirements').val();
            var file = $('#estimate_file')[0].files[0];
            var hourlyRate = $('#hourly_rate').val();
            
            if (!requirements && !file) {
                alert('Please provide requirements or upload a file');
                return;
            }
            
            if (requirements) {
                formData.append('requirements', requirements);
            }
            if (file) {
                formData.append('file', file);
            }
            if (hourlyRate) {
                formData.append('hourly_rate', hourlyRate);
            }
            
            $.ajax({
                url: '<?php echo admin_url('admin-ajax.php'); ?>',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function(response) {
                    if (response.success) {
                        var data = response.data;
                        $('#time-min').text(data.estimated_time_hours_min);
                        $('#time-max').text(data.estimated_time_hours_max);
                        $('#cost-min').text(data.estimated_cost_min.toFixed(2));
                        $('#cost-max').text(data.estimated_cost_max.toFixed(2));
                        $('#estimate-result').show();
                    } else {
                        alert('Error: ' + response.data);
                    }
                },
                error: function() {
                    alert('An error occurred. Please try again.');
                }
            });
        });
    });
    </script>
    <?php
    return ob_get_clean();
}
add_shortcode('estimation_form', 'estimation_form_shortcode');
```

---

## AJAX Handler for WordPress

Add this to handle AJAX requests:

```php
/**
 * AJAX handler for estimation request
 */
function handle_estimation_request() {
    check_ajax_referer('estimation_nonce', 'nonce');
    
    $requirements = isset($_POST['requirements']) ? sanitize_textarea_field($_POST['requirements']) : '';
    $hourly_rate = isset($_POST['hourly_rate']) ? floatval($_POST['hourly_rate']) : 30;
    
    // Handle file upload
    $file_path = '';
    if (!empty($_FILES['file']['tmp_name'])) {
    $uploaded_file = $_FILES['file'];
    $allowed_types = array(
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain'
    );
    $allowed_extensions = array('pdf', 'docx', 'doc', 'txt');
    $file_ext = strtolower(pathinfo($uploaded_file['name'], PATHINFO_EXTENSION));
    
    if (in_array($uploaded_file['type'], $allowed_types) || in_array($file_ext, $allowed_extensions)) {
            $upload_dir = wp_upload_dir();
            $file_path = $upload_dir['path'] . '/' . $uploaded_file['name'];
            move_uploaded_file($uploaded_file['tmp_name'], $file_path);
        }
    }
    
    // Get estimate from API
    global $estimation_bot;
    $result = $estimation_bot->get_estimate($requirements, $file_path, $hourly_rate);
    
    // Clean up uploaded file
    if (!empty($file_path) && file_exists($file_path)) {
        unlink($file_path);
    }
    
    if (is_wp_error($result)) {
        wp_send_json_error($result->get_error_message());
    } else {
        wp_send_json_success($result);
    }
}
add_action('wp_ajax_get_estimate', 'handle_estimation_request');
add_action('wp_ajax_nopriv_get_estimate', 'handle_estimation_request');
```

---

## JavaScript/jQuery Integration

Standalone JavaScript example (can be used in WordPress):

```javascript
class EstimationBot {
    constructor(apiUrl) {
        this.apiUrl = apiUrl || 'https://your-railway-app.railway.app/api/v1';
    }
    
    async getEstimate(requirements, file, hourlyRate = 30) {
        const formData = new FormData();
        
        if (requirements) {
            formData.append('requirements', requirements);
        }
        if (file) {
            formData.append('file', file);
        }
        if (hourlyRate) {
            formData.append('hourly_rate', hourlyRate.toString());
        }
        
        try {
            const response = await fetch(`${this.apiUrl}/estimate`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to get estimate');
            }
            
            const data = await response.json();
            return {
                success: true,
                data: {
                    timeMin: data.estimated_time_hours_min,
                    timeMax: data.estimated_time_hours_max,
                    costMin: data.estimated_cost_min,
                    costMax: data.estimated_cost_max
                }
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    async checkHealth() {
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            return response.ok;
        } catch {
            return false;
        }
    }
}

// Usage
const estimationBot = new EstimationBot('https://your-railway-app.railway.app/api/v1');

// Get estimate
estimationBot.getEstimate('I want to add HYP payment method', null, 30)
    .then(result => {
        if (result.success) {
            console.log('Time:', result.data.timeMin, '-', result.data.timeMax, 'hours');
            console.log('Cost: $', result.data.costMin, '- $', result.data.costMax);
        } else {
            console.error('Error:', result.error);
        }
    });
```

---

## Response Data Structure

### Success Response

```json
{
  "estimated_time_hours_min": 38.0,
  "estimated_time_hours_max": 42.0,
  "estimated_cost_min": 1140.00,
  "estimated_cost_max": 1260.00
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `estimated_time_hours_min` | float | Minimum estimated time in hours |
| `estimated_time_hours_max` | float | Maximum estimated time in hours |
| `estimated_cost_min` | float | Minimum estimated cost in USD |
| `estimated_cost_max` | float | Maximum estimated cost in USD |

---

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "detail": "Could not extract features from requirements. Please provide more specific details about the features you need."
}
```

**400 Bad Request (No input):**
```json
{
  "detail": "Please provide either text requirements or upload a PDF/DOCX file (or both)."
}
```

**400 Bad Request (Invalid file):**
```json
{
  "detail": "Unsupported file type: .xyz. Please upload PDF, DOCX, DOC, or TXT files."
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Error generating estimate: [error message]"
}
```

---

## WordPress Integration Best Practices

### 1. Security

- Always use nonces for AJAX requests
- Sanitize all user inputs
- Validate file types and sizes
- Use WordPress HTTP API (handles SSL automatically)

### 2. Error Handling

```php
$result = $estimation_bot->get_estimate($requirements, $file_path);

if (is_wp_error($result)) {
    $error_message = $result->get_error_message();
    // Log error
    error_log('Estimation Bot Error: ' . $error_message);
    // Display user-friendly message
    echo '<div class="error">Unable to generate estimate. Please try again.</div>';
} else {
    // Display results
    echo '<div class="estimate-result">';
    echo '<p>Time: ' . $result['estimated_time_hours_min'] . ' - ' . $result['estimated_time_hours_max'] . ' hours</p>';
    echo '<p>Cost: $' . number_format($result['estimated_cost_min'], 2) . ' - $' . number_format($result['estimated_cost_max'], 2) . '</p>';
    echo '</div>';
}
```

### 3. Caching

Consider caching estimates for identical requests:

```php
function get_cached_estimate($requirements, $file_path = '', $hourly_rate = 30) {
    $cache_key = 'estimate_' . md5($requirements . $file_path . $hourly_rate);
    $cached = get_transient($cache_key);
    
    if ($cached !== false) {
        return $cached;
    }
    
    global $estimation_bot;
    $result = $estimation_bot->get_estimate($requirements, $file_path, $hourly_rate);
    
    if (!is_wp_error($result)) {
        set_transient($cache_key, $result, HOUR_IN_SECONDS); // Cache for 1 hour
    }
    
    return $result;
}
```

### 4. File Upload Handling

```php
function handle_estimation_file_upload() {
    if (!function_exists('wp_handle_upload')) {
        require_once(ABSPATH . 'wp-admin/includes/file.php');
    }
    
    $uploaded_file = $_FILES['file'];
    $allowed_types = array('pdf', 'docx', 'doc', 'txt');
    $file_ext = strtolower(pathinfo($uploaded_file['name'], PATHINFO_EXTENSION));
    
    if (!in_array($file_ext, $allowed_types)) {
        return new WP_Error('invalid_file', 'Only PDF, DOCX, DOC, and TXT files are allowed');
    }
    
    $upload_overrides = array('test_form' => false);
    $movefile = wp_handle_upload($uploaded_file, $upload_overrides);
    
    if ($movefile && !isset($movefile['error'])) {
        return $movefile['file'];
    } else {
        return new WP_Error('upload_error', $movefile['error']);
    }
}
```

---

## Complete WordPress Plugin Example

Create a file `estimation-bot-integration.php`:

```php
<?php
/**
 * Plugin Name: Estimation Bot Integration
 * Description: Integrate Estimation Bot API into WordPress
 * Version: 1.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

class EstimationBotIntegration {
    private $api_base_url;
    
    public function __construct() {
        $this->api_base_url = get_option('estimation_bot_api_url', 'https://your-railway-app.railway.app/api/v1');
        
        add_action('wp_enqueue_scripts', array($this, 'enqueue_scripts'));
        add_shortcode('estimation_bot', array($this, 'render_shortcode'));
        add_action('wp_ajax_get_estimate', array($this, 'ajax_get_estimate'));
        add_action('wp_ajax_nopriv_get_estimate', array($this, 'ajax_get_estimate'));
        add_action('admin_menu', array($this, 'add_admin_menu'));
    }
    
    public function enqueue_scripts() {
        wp_enqueue_script('jquery');
        wp_enqueue_script('estimation-bot', plugin_dir_url(__FILE__) . 'js/estimation-bot.js', array('jquery'), '1.0.0', true);
        wp_localize_script('estimation-bot', 'estimationBot', array(
            'ajax_url' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('estimation_nonce')
        ));
    }
    
    public function render_shortcode($atts) {
        // Shortcode implementation (from previous example)
        // ...
    }
    
    public function ajax_get_estimate() {
        check_ajax_referer('estimation_nonce', 'nonce');
        
        $requirements = isset($_POST['requirements']) ? sanitize_textarea_field($_POST['requirements']) : '';
        $hourly_rate = isset($_POST['hourly_rate']) ? floatval($_POST['hourly_rate']) : 30;
        
        // Handle file upload and API call
        // ...
    }
    
    public function add_admin_menu() {
        add_options_page(
            'Estimation Bot Settings',
            'Estimation Bot',
            'manage_options',
            'estimation-bot',
            array($this, 'render_settings_page')
        );
    }
    
    public function render_settings_page() {
        if (isset($_POST['submit'])) {
            update_option('estimation_bot_api_url', sanitize_text_field($_POST['api_url']));
            echo '<div class="notice notice-success"><p>Settings saved!</p></div>';
        }
        
        $api_url = get_option('estimation_bot_api_url', 'https://your-railway-app.railway.app/api/v1');
        ?>
        <div class="wrap">
            <h1>Estimation Bot Settings</h1>
            <form method="post">
                <table class="form-table">
                    <tr>
                        <th><label for="api_url">API Base URL</label></th>
                        <td><input type="text" id="api_url" name="api_url" value="<?php echo esc_attr($api_url); ?>" class="regular-text"></td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
        </div>
        <?php
    }
}

new EstimationBotIntegration();
```

---

## Testing

### Test API Connection

```php
$estimation_bot = new EstimationBotAPI();
$is_healthy = $estimation_bot->check_health();

if ($is_healthy) {
    echo 'API is running';
} else {
    echo 'API is not accessible';
}
```

### Test Estimate Request

```php
$result = $estimation_bot->get_estimate(
    'I want to add rating and review for rider',
    '',
    30
);

if (!is_wp_error($result)) {
    echo 'Time: ' . $result['estimated_time_hours_min'] . ' - ' . $result['estimated_time_hours_max'] . ' hours';
    echo 'Cost: $' . $result['estimated_cost_min'] . ' - $' . $result['estimated_cost_max'];
} else {
    echo 'Error: ' . $result->get_error_message();
}
```

---

## Support

For API issues or questions:
- Check API health: `GET /api/v1/health`
- Verify API URL is correct
- Check file upload size limits
- Ensure CORS is configured correctly

---

## Notes

- Default hourly rate: $30/hour
- Estimates are returned as ranges (min-max)
- Supported file types: PDF, DOCX, DOC, TXT
- File uploads are temporary and cleaned up after processing
- API timeout: 60 seconds recommended
- Maximum file size: Check your server's `upload_max_filesize` setting
- Note: .doc files may need to be converted to .docx for best extraction results