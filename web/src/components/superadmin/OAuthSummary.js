import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import ThemedLoading from '../ui/ThemedLoading';

const OAuthSummary = ({ getApiClient }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedOrgs, setExpandedOrgs] = useState(new Set());

  useEffect(() => {
    fetchOAuthSummary();
  }, []);

  const fetchOAuthSummary = async () => {
    try {
      setLoading(true);
      const client = getApiClient();
      const response = await client.get('/api/superadmin/organizations/oauth/summary');
      setSummary(response.data);
    } catch (error) {
      console.error('Error fetching OAuth summary:', error);
      toast.error('Failed to load OAuth summary');
    } finally {
      setLoading(false);
    }
  };

  const toggleOrgExpansion = (orgId) => {
    setExpandedOrgs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(orgId)) {
        newSet.delete(orgId);
      } else {
        newSet.add(orgId);
      }
      return newSet;
    });
  };

  const getStatusColor = (enabled) => {
    return enabled ? 'text-green-600' : 'text-red-600';
  };

  const getStatusIcon = (enabled) => {
    return enabled ? '✓' : '✗';
  };

  if (loading) {
    return <ThemedLoading />;
  }

  if (!summary) {
    return null;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
          OAuth Configuration Summary
        </h3>
        <button
          onClick={fetchOAuthSummary}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {/* Summary Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg text-center">
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {summary.total_organizations}
          </div>
          <div className="text-sm text-blue-600 dark:text-blue-400">Total Organizations</div>
        </div>
        
        <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg text-center">
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {summary.oauth_enabled_count}
          </div>
          <div className="text-sm text-green-600 dark:text-green-400">OAuth Enabled</div>
        </div>
        
        <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg text-center">
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {summary.oauth_configured_count}
          </div>
          <div className="text-sm text-purple-600 dark:text-purple-400">Fully Configured</div>
        </div>
        
        <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg text-center">
          <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
            {summary.organizations_with_domains}
          </div>
          <div className="text-sm text-yellow-600 dark:text-yellow-400">With Domains</div>
        </div>
        
        <div className="bg-indigo-50 dark:bg-indigo-900/20 p-4 rounded-lg text-center">
          <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
            {summary.organizations_with_callbacks}
          </div>
          <div className="text-sm text-indigo-600 dark:text-indigo-400">With Callbacks</div>
        </div>
      </div>

      {/* Organization Details */}
      <div className="space-y-4">
        <h4 className="text-lg font-medium text-gray-900 dark:text-white">
          Organization Details
        </h4>
        
        {summary.organizations_details.map((org) => (
          <div key={org.id} className="border border-gray-200 dark:border-gray-700 rounded-lg">
            <div 
              className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
              onClick={() => toggleOrgExpansion(org.id)}
            >
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <span className={`text-lg ${getStatusColor(org.oauth_enabled)}`}>
                    {getStatusIcon(org.oauth_enabled)}
                  </span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {org.name}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    ({org.prefix})
                  </span>
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <span className={`text-sm ${getStatusColor(org.oauth_enabled)}`}>
                    {getStatusIcon(org.oauth_enabled)} OAuth
                  </span>
                  <span className={`text-sm ${getStatusColor(org.storefront_enabled)}`}>
                    {getStatusIcon(org.storefront_enabled)} Store
                  </span>
                </div>
                <div className="text-gray-400">
                  {expandedOrgs.has(org.id) ? '▼' : '▶'}
                </div>
              </div>
            </div>
            
            {expandedOrgs.has(org.id) && (
              <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-700">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h5 className="font-medium text-gray-900 dark:text-white mb-2">OAuth Configuration</h5>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">OAuth Enabled:</span>
                        <span className={getStatusColor(org.oauth_enabled)}>
                          {org.oauth_enabled ? 'Yes' : 'No'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Callback URL:</span>
                        <span className="text-gray-900 dark:text-white">
                          {org.oauth_callback_url || 'Not configured'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Allowed Domains:</span>
                        <span className="text-gray-900 dark:text-white">
                          {org.allowed_domains ? org.allowed_domains.length : 0}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h5 className="font-medium text-gray-900 dark:text-white mb-2">Domain List</h5>
                    <div className="space-y-1">
                      {org.allowed_domains && org.allowed_domains.length > 0 ? (
                        org.allowed_domains.map((domain, index) => (
                          <div key={index} className="text-sm text-gray-700 dark:text-gray-300">
                            • {domain}
                          </div>
                        ))
                      ) : (
                        <div className="text-sm text-gray-500 italic">No domains configured</div>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Status: {org.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <div className="flex space-x-2">
                      {org.oauth_enabled && (
                        <span className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 text-xs rounded-full">
                          OAuth Ready
                        </span>
                      )}
                      {org.storefront_enabled && (
                        <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 text-xs rounded-full">
                          Storefront
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default OAuthSummary;

