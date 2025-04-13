import { healthService } from '../api/apiService';

/**
 * Check the API status and return a promise with the result
 * @returns {Promise<Object>} Object with status information
 */
export const checkApiStatus = async () => {
  try {
    const response = await healthService.getStatus();
    if (response.success) {
      return {
        isHealthy: response.data.health === 'healthy',
        data: response.data,
        error: null
      };
    } else {
      throw new Error(response.error || 'Failed to fetch system status');
    }
  } catch (error) {
    console.error('Error checking API status:', error);
    return {
      isHealthy: false,
      data: null,
      error: error.message
    };
  }
};