import React, { useState, useCallback } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Grid,
  Paper,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
} from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { RootState } from '../../store/store';
import { ConversationNode, ConversationFlow } from '../../types/voiceAssistant';

interface NodeDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (node: Partial<ConversationNode>) => void;
  node?: ConversationNode;
}

const NodeDialog: React.FC<NodeDialogProps> = ({ open, onClose, onSave, node }) => {
  const [nodeData, setNodeData] = useState<Partial<ConversationNode>>({
    type: 'trigger',
    data: { label: '', content: '' },
    ...node,
  });

  const handleSave = () => {
    onSave(nodeData);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {node ? 'Edit Node' : 'Create New Node'}
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Node Type</InputLabel>
              <Select
                value={nodeData.type || 'trigger'}
                label="Node Type"
                onChange={(e) => setNodeData({ ...nodeData, type: e.target.value as ConversationNode['type'] })}
              >
                <MenuItem value="trigger">Trigger</MenuItem>
                <MenuItem value="response">Response</MenuItem>
                <MenuItem value="condition">Condition</MenuItem>
                <MenuItem value="action">Action</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Node Label"
              value={nodeData.data?.label || ''}
              onChange={(e) => setNodeData({
                ...nodeData,
                data: { ...nodeData.data, label: e.target.value }
              })}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Content"
              placeholder="Enter the content for this node..."
              value={nodeData.data?.content || ''}
              onChange={(e) => setNodeData({
                ...nodeData,
                data: { 
                  ...nodeData.data, 
                  label: nodeData.data?.label || '',
                  content: e.target.value 
                }
              })}
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained">
          {node ? 'Update' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const ConversationFlowBuilder: React.FC = () => {
  const { currentConfig } = useSelector((state: RootState) => state.configuration);
  const [selectedFlow, setSelectedFlow] = useState<ConversationFlow | null>(null);
  const [nodeDialogOpen, setNodeDialogOpen] = useState(false);
  const [editingNode, setEditingNode] = useState<ConversationNode | undefined>();
  const [flowDialogOpen, setFlowDialogOpen] = useState(false);
  const [newFlowName, setNewFlowName] = useState('');
  const [newFlowDescription, setNewFlowDescription] = useState('');

  const handleCreateFlow = () => {
    if (!newFlowName.trim()) return;

    const newFlow: ConversationFlow = {
      id: `flow-${Date.now()}`,
      name: newFlowName,
      description: newFlowDescription,
      nodes: [],
      isActive: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setSelectedFlow(newFlow);
    setFlowDialogOpen(false);
    setNewFlowName('');
    setNewFlowDescription('');
  };

  const handleCreateNode = useCallback(() => {
    setEditingNode(undefined);
    setNodeDialogOpen(true);
  }, []);

  const handleEditNode = useCallback((node: ConversationNode) => {
    setEditingNode(node);
    setNodeDialogOpen(true);
  }, []);

  const handleSaveNode = useCallback((nodeData: Partial<ConversationNode>) => {
    if (!selectedFlow) return;

    if (editingNode) {
      // Update existing node
      const updatedNodes = selectedFlow.nodes.map(node =>
        node.id === editingNode.id ? { ...node, ...nodeData } : node
      );
      setSelectedFlow({ ...selectedFlow, nodes: updatedNodes });
    } else {
      // Create new node
      const newNode: ConversationNode = {
        id: `node-${Date.now()}`,
        type: nodeData.type || 'trigger',
        position: { x: Math.random() * 400, y: Math.random() * 300 },
        data: nodeData.data || { label: '', content: '' },
        connections: [],
        ...nodeData,
      };
      setSelectedFlow({
        ...selectedFlow,
        nodes: [...selectedFlow.nodes, newNode],
      });
    }
  }, [selectedFlow, editingNode]);

  const handleDeleteNode = useCallback((nodeId: string) => {
    if (!selectedFlow) return;
    
    const updatedNodes = selectedFlow.nodes.filter(node => node.id !== nodeId);
    setSelectedFlow({ ...selectedFlow, nodes: updatedNodes });
  }, [selectedFlow]);

  const getNodeTypeColor = (type: ConversationNode['type']) => {
    switch (type) {
      case 'trigger': return 'primary';
      case 'response': return 'secondary';
      case 'condition': return 'warning';
      case 'action': return 'success';
      default: return 'default';
    }
  };

  if (!currentConfig) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Conversation Flow Builder
          </Typography>
          <Typography color="textSecondary">
            Please create a configuration first.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Conversation Flow Builder
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setFlowDialogOpen(true)}
          >
            New Flow
          </Button>
        </Box>

        <Typography variant="body2" color="textSecondary" paragraph>
          Design conversation flows with drag-and-drop nodes for triggers, responses, conditions, and actions.
        </Typography>

        {/* Flow Selection */}
        {currentConfig.conversationFlows.length > 0 && (
          <Box mb={3}>
            <Typography variant="subtitle2" gutterBottom>
              Existing Flows
            </Typography>
            <Grid container spacing={2}>
              {currentConfig.conversationFlows.map((flow) => (
                <Grid item xs={12} sm={6} md={4} key={flow.id}>
                  <Paper
                    sx={{
                      p: 2,
                      cursor: 'pointer',
                      border: selectedFlow?.id === flow.id ? 2 : 1,
                      borderColor: selectedFlow?.id === flow.id ? 'primary.main' : 'divider',
                    }}
                    onClick={() => setSelectedFlow(flow)}
                  >
                    <Typography variant="subtitle2">{flow.name}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      {flow.description}
                    </Typography>
                    <Box mt={1}>
                      <Chip
                        label={flow.isActive ? 'Active' : 'Inactive'}
                        size="small"
                        color={flow.isActive ? 'success' : 'default'}
                      />
                      <Chip
                        label={`${flow.nodes.length} nodes`}
                        size="small"
                        sx={{ ml: 1 }}
                      />
                    </Box>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Flow Builder Canvas */}
        {selectedFlow && (
          <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">
                {selectedFlow.name}
              </Typography>
              <Box>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={handleCreateNode}
                  sx={{ mr: 1 }}
                >
                  Add Node
                </Button>
                <Button
                  variant="contained"
                  startIcon={selectedFlow.isActive ? <StopIcon /> : <PlayIcon />}
                  color={selectedFlow.isActive ? 'error' : 'success'}
                >
                  {selectedFlow.isActive ? 'Deactivate' : 'Activate'}
                </Button>
              </Box>
            </Box>

            {/* Canvas Area */}
            <Paper
              sx={{
                minHeight: 400,
                p: 2,
                backgroundColor: 'grey.50',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {selectedFlow.nodes.length === 0 ? (
                <Box
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                  justifyContent="center"
                  height="100%"
                  color="text.secondary"
                >
                  <Typography variant="h6" gutterBottom>
                    Empty Flow
                  </Typography>
                  <Typography variant="body2" paragraph>
                    Start building your conversation flow by adding nodes.
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleCreateNode}
                  >
                    Add First Node
                  </Button>
                </Box>
              ) : (
                <Grid container spacing={2}>
                  {selectedFlow.nodes.map((node) => (
                    <Grid item xs={12} sm={6} md={4} key={node.id}>
                      <Paper
                        sx={{
                          p: 2,
                          border: 1,
                          borderColor: 'divider',
                          position: 'relative',
                        }}
                      >
                        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                          <Chip
                            label={node.type}
                            size="small"
                            color={getNodeTypeColor(node.type) as any}
                          />
                          <Box>
                            <Tooltip title="Edit Node">
                              <IconButton
                                size="small"
                                onClick={() => handleEditNode(node)}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Delete Node">
                              <IconButton
                                size="small"
                                onClick={() => handleDeleteNode(node.id)}
                                color="error"
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </Box>
                        <Typography variant="subtitle2" gutterBottom>
                          {node.data.label}
                        </Typography>
                        {node.data.content && (
                          <Typography variant="body2" color="textSecondary">
                            {node.data.content.length > 100
                              ? `${node.data.content.substring(0, 100)}...`
                              : node.data.content
                            }
                          </Typography>
                        )}
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              )}
            </Paper>
          </Box>
        )}

        {/* New Flow Dialog */}
        <Dialog open={flowDialogOpen} onClose={() => setFlowDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Create New Conversation Flow</DialogTitle>
          <DialogContent>
            <TextField
              fullWidth
              label="Flow Name"
              value={newFlowName}
              onChange={(e) => setNewFlowName(e.target.value)}
              sx={{ mt: 2, mb: 2 }}
            />
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Description"
              value={newFlowDescription}
              onChange={(e) => setNewFlowDescription(e.target.value)}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setFlowDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateFlow} variant="contained">
              Create Flow
            </Button>
          </DialogActions>
        </Dialog>

        {/* Node Dialog */}
        <NodeDialog
          open={nodeDialogOpen}
          onClose={() => setNodeDialogOpen(false)}
          onSave={handleSaveNode}
          node={editingNode}
        />
      </CardContent>
    </Card>
  );
};

export default ConversationFlowBuilder;