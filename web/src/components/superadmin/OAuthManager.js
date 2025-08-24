import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import ThemedLoading from '../ui/ThemedLoading';

const OAuthManager = ({ organization, onUpdate, getApiClient }) => {
  const [oauthSettings, setOauthSettings] = useState({
    oauth_enabled: false,
    oauth_callback_url: '',
    allowed_domains: []
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResults, setTestResults] = useState(null);
  const [newDomain, setNewDomain] = useState('');
  const [showTestResults, setShowTestResults] = useState(false);

  useEffect(() => {
    if (organization) {
      setOauthSettings({
        oauth_enabled: organization.oauth_enabled || false,
        oauth_callback_url: organization.oauth_callback_url || '',
        allowed_domains: organization.allowed_domains || []
      });
    }
  }, [organization]);

  const fetchOAuthSettings = async () => {
    try {
      setLoading(true);
      const client = getApiClient();
      const response = await client.get(`/api/superadmin/organizations/${organization.id}/oauth`);
      setOauthSettings(response.data);
    } catch (error) {
      console.error('Error fetching OAuth settings:', error);
      toast.error('Failed to load OAuth settings');
    } finally {
      setLoading(false);
    }
  };

  const saveOAuthSettings = async () => {
    try {
      setSaving(true);
      const client = getApiClient();
      const response = await client.put(`/api/superadmin/organizations/${organization.id}/oauth`, oauthSettings);
      
      toast.success('OAuth settings saved successfully');
      if (onUpdate) {
        onUpdate(response.data.organization);
      }
    } catch (error) {
      console.error('Error saving OAuth settings:', error);
      toast.error('Failed to save OAuth settings: ' + (error.response?.data?.error || error.message));
    } finally {
      setSaving(false);
    }
  };

  const testOAuthConfiguration = async () => {
    try {
      setTesting(true);
      const client = getApiClient();
      const response = await client.post(`/api/superadmin/organizations/${organization.id}/oauth/test`);
      setTestResults(response.data);
      setShowTestResults(true);
    } catch (error) {
      console.error('Error testing OAuth configuration:', error);
      toast.error('Failed to test OAuth configuration');
    } finally {
      setTesting(false);
    }
  };

  const addDomain = () => {
    if (newDomain.trim() && !oauthSettings.allowed_domains.includes(newDomain.trim())) {
      setOauthSettings(prev => ({
        ...prev,
        allowed_domains: [...prev.allowed_domains, newDomain.trim()]
      }));
      setNewDomain('');
    }
  };

  const removeDomain = (domainToRemove) => {
    setOauthSettings(prev => ({
      ...prev,
      allowed_domains: prev.allowed_domains.filter(domain => domain !== domainToRemove)
    }));
  };

  const handleDomainKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addDomain();
    }
  };

  if (loading) {
    return <ThemedLoading />;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          OAuth Configuration for {organization.name}
        </h3>
        <button
          onClick={testOAuthConfiguration}
          disabled={testing}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {testing ? 'Testing...' : 'Test Configuration'}
        </button>
      </div>

      {/* OAuth Enable/Disable */}
      <div className="mb-4">
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={oauthSettings.oauth_enabled}
            onChange={(e) => setOauthSettings(prev => ({ ...prev, oauth_enabled: e.target.checked }))}
            className="mr-2"
          />
          <span className="text-gray-700 dark:text-gray-300">Enable OAuth for this organization</span>
        </label>
      </div>

      {/* Callback URL */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          OAuth Callback URL
        </label>
        <input
          type="url"
          value={oauthSettings.oauth_callback_url}
          onChange={(e) => setOauthSettings(prev => ({ ...prev, oauth_callback_url: e.target.value }))}
          placeholder="https://partner.com/auth/callback"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-sm text-gray-500 mt-1">
          The URL where users will be redirected after OAuth authentication
        </p>
      </div>

      {/* Allowed Domains */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Allowed Domains
        </label>
        <div className="flex mb-2">
          <input
            type="text"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            onKeyPress={handleDomainKeyPress}
            placeholder="example.com"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={addDomain}
            className="px-4 py-2 bg-green-600 text-white rounded-r-md hover:bg-green-700"
          >
            Add
          </button>
        </div>
        <p className="text-sm text-gray-500 mb-2">
          Only these domains will be allowed to initiate OAuth flows for this organization
        </p>
        
        {/* Domain List */}
        <div className="space-y-2">
          {oauthSettings.allowed_domains.map((domain, index) => (
            <div key={index} className="flex items-center justify-between bg-gray-50 dark:bg-gray-700 px-3 py-2 rounded-md">
              <span className="text-gray-700 dark:text-gray-300">{domain}</span>
              <button
                onClick={() => removeDomain(domain)}
                className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
              >
                Remove
              </button>
            </div>
          ))}
          {oauthSettings.allowed_domains.length === 0 && (
            <p className="text-sm text-gray-500 italic">No domains configured</p>
          )}
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={saveOAuthSettings}
          disabled={saving}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save OAuth Settings'}
        </button>
      </div>

      {/* Test Results Modal */}
      {showTestResults && testResults && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                OAuth Configuration Test Results
              </h3>
              <button
                onClick={() => setShowTestResults(false)}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                  <span className="font-medium">OAuth Enabled:</span>
                  <span className={`ml-2 ${testResults.oauth_config.oauth_enabled ? 'text-green-600' : 'text-red-600'}`}>
                    {testResults.oauth_config.oauth_enabled ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                  <span className="font-medium">Has Callback URL:</span>
                  <span className={`ml-2 ${testResults.oauth_config.has_callback_url ? 'text-green-600' : 'text-red-600'}`}>
                    {testResults.oauth_config.has_callback_url ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                  <span className="font-medium">Has Allowed Domains:</span>
                  <span className={`ml-2 ${testResults.oauth_config.has_allowed_domains ? 'text-green-600' : 'text-red-600'}`}>
                    {testResults.oauth_config.has_allowed_domains ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                  <span className="font-medium">Domains Count:</span>
                  <span className="ml-2">{testResults.oauth_config.domains_count}</span>
                </div>
              </div>

              {testResults.oauth_config.callback_url_valid !== undefined && (
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                  <span className="font-medium">Callback URL Valid:</span>
                  <span className={`ml-2 ${testResults.oauth_config.callback_url_valid ? 'text-green-600' : 'text-red-600'}`}>
                    {testResults.oauth_config.callback_url_valid ? 'Yes' : 'No'}
                  </span>
                  {!testResults.oauth_config.callback_url_valid && (
                    <p className="text-red-600 mt-1">{testResults.oauth_config.callback_url_error}</p>
                  )}
                </div>
              )}

              {testResults.oauth_config.valid_domains && testResults.oauth_config.valid_domains.length > 0 && (
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                  <span className="font-medium text-green-600">Valid Domains:</span>
                  <div className="mt-2 space-y-1">
                    {testResults.oauth_config.valid_domains.map((domain, index) => (
                      <div key={index} className="text-sm text-gray-700 dark:text-gray-300">
                        ✓ {domain}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {testResults.oauth_config.invalid_domains && testResults.oauth_config.invalid_domains.length > 0 && (
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                  <span className="font-medium text-red-600">Invalid Domains:</span>
                  <div className="mt-2 space-y-1">
                    {testResults.oauth_config.invalid_domains.map((domain, index) => (
                      <div key={index} className="text-sm text-gray-700 dark:text-gray-300">
                        ✗ {domain}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                <span className="font-medium">Configuration Status:</span>
                <span className={`ml-2 ${testResults.oauth_config.all_domains_valid ? 'text-green-600' : 'text-red-600'}`}>
                  {testResults.oauth_config.all_domains_valid ? 'Fully Configured' : 'Needs Attention'}
                </span>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowTestResults(false)}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OAuthManager;

