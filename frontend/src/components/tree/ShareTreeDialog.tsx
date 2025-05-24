import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import api from '@/api';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog';
import { 
  Form, 
  FormField, 
  FormItem, 
  FormLabel, 
  FormControl, 
  FormMessage 
} from '@/components/ui/form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { Loader2, Trash } from 'lucide-react';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from '@/components/ui/use-toast';

const permissionSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email address' }),
  permission: z.enum(['view', 'edit', 'admin'], {
    required_error: 'Please select a permission level',
  }),
});

interface ShareTreeDialogProps {
  isOpen: boolean;
  onClose: () => void;
  treeId: string;
  treeName: string;
}

interface SharedUser {
  id: string;
  email: string;
  username: string;
  permission: 'view' | 'edit' | 'admin';
}

export function ShareTreeDialog({ isOpen, onClose, treeId, treeName }: ShareTreeDialogProps) {
  const { user } = useAuth();
  const [sharedUsers, setSharedUsers] = useState<SharedUser[]>([]);
  const [loading, setLoading] = useState(false);

  const form = useForm<z.infer<typeof permissionSchema>>({
    resolver: zodResolver(permissionSchema),
    defaultValues: {
      email: '',
      permission: 'view',
    },
  });

  const loadSharedUsers = async () => {
    if (!treeId) return;
    
    setLoading(true);
    try {
      const response = await api.getTreePermissions(treeId);
      setSharedUsers(response.shared_users || []);
    } catch (error) {
      console.error('Failed to load shared users:', error);
      toast({
        title: 'Error',
        description: 'Failed to load shared users',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadSharedUsers();
    }
  }, [isOpen, treeId]);

  const onSubmit = async (data: z.infer<typeof permissionSchema>) => {
    setLoading(true);
    try {
      await api.shareTree(treeId, {
        email: data.email,
        permission_level: data.permission,
      });
      
      // Reset form
      form.reset({
        email: '',
        permission: 'view',
      });
      
      // Reload shared users
      await loadSharedUsers();
      
      toast({
        title: 'Success',
        description: `Invitation sent to ${data.email}`,
      });
    } catch (error: any) {
      console.error('Failed to share tree:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.message || 'Failed to share tree',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const removeUserAccess = async (userId: string) => {
    if (!confirm('Are you sure you want to remove this user\'s access?')) {
      return;
    }
    
    setLoading(true);
    try {
      await api.revokeTreeAccess(treeId, userId);
      await loadSharedUsers();
      toast({
        title: 'Success',
        description: 'User access removed',
      });
    } catch (error) {
      console.error('Failed to remove user access:', error);
      toast({
        title: 'Error',
        description: 'Failed to remove user access',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const updatePermission = async (userId: string, newPermission: string) => {
    setLoading(true);
    try {
      await api.updateTreePermission(treeId, userId, newPermission);
      await loadSharedUsers();
      toast({
        title: 'Success',
        description: 'Permission updated',
      });
    } catch (error) {
      console.error('Failed to update permission:', error);
      toast({
        title: 'Error',
        description: 'Failed to update permission',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Share "{treeName}"</DialogTitle>
        </DialogHeader>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter email address" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <FormField
              control={form.control}
              name="permission"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Permission</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select permission level" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="view">Can View</SelectItem>
                      <SelectItem value="edit">Can Edit</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Share
            </Button>
          </form>
        </Form>
        
        <div className="mt-6">
          <h3 className="text-lg font-medium">People with access</h3>
          
          {loading ? (
            <div className="flex justify-center my-4">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : sharedUsers.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Permission</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sharedUsers.map((sharedUser) => (
                  <TableRow key={sharedUser.id}>
                    <TableCell>{sharedUser.email}</TableCell>
                    <TableCell>
                      <Select
                        defaultValue={sharedUser.permission}
                        onValueChange={(value) => updatePermission(sharedUser.id, value)}
                        disabled={user?.id === sharedUser.id}
                      >
                        <SelectTrigger className="w-[100px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="view">View</SelectItem>
                          <SelectItem value="edit">Edit</SelectItem>
                          <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell>
                      {user?.id !== sharedUser.id && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeUserAccess(sharedUser.id)}
                        >
                          <Trash className="h-4 w-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground py-2">
              No one else has access to this tree yet.
            </p>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
