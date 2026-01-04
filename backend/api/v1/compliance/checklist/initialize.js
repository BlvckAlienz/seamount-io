// backend/api/v1/compliance/checklist/initialize.js
const { createClient } = require('@supabase/supabase-js');

module.exports = async (req, res) => {
  try {
    const supabase = createClient(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_SERVICE_ROLE_KEY
    );
    
    const { user } = req;
    
    if (!user) {
      return res.status(401).json({ success: false, error: 'Unauthorized' });
    }
    
    // Check if user already has checklist items
    const { data: existingChecklist, error: existingError } = await supabase
      .from('audit_checklist_items')
      .select('*')
      .eq('user_id', user.id);
    
    if (existingError) {
      console.error('Error checking existing checklist:', existingError);
    }
    
    if (existingChecklist && existingChecklist.length > 0) {
      return res.status(200).json({ 
        success: true, 
        message: 'Checklist already exists',
        checklist: existingChecklist
      });
    }
    
    // Initialize user checklist from templates using the PostgreSQL function
    const { data: newChecklist, error: initError } = await supabase.rpc(
      'initialize_user_checklist',
      { user_uuid: user.id }
    );
    
    if (initError) {
      throw initError;
    }
    
    return res.status(200).json({
      success: true,
      message: 'Checklist initialized successfully',
      checklist: newChecklist
    });
    
  } catch (error) {
    console.error('Error initializing checklist:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to initialize checklist'
    });
  }
};