import * as React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { useTree } from "@/contexts/TreeContext";
import api from "@/api";

interface TreeSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function TreeSettingsModal({ isOpen, onClose }: TreeSettingsModalProps) {
  const { activeTree, refreshTrees } = useTree();
  const { toast } = useToast();
  const [loading, setLoading] = React.useState(false);
  const [settings, setSettings] = React.useState({
    privacy_setting: activeTree?.privacy_setting || "PRIVATE",
    description: activeTree?.description || "",
  });

  React.useEffect(() => {
    if (activeTree) {
      setSettings({
        privacy_setting: activeTree.privacy_setting,
        description: activeTree.description || "",
      });
    }
  }, [activeTree]);

  const handleSave = async () => {
    if (!activeTree) return;

    setLoading(true);
    try {
      await api.updateTree(activeTree.id, settings);
      await refreshTrees();
      toast({
        title: "Settings Updated",
        description: "Tree settings have been successfully updated.",
      });
      onClose();
    } catch (error) {
      console.error("Failed to update tree settings:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to update tree settings. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  };

  if (!activeTree) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Tree Settings</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="privacy">Privacy Setting</Label>
            <Select
              value={settings.privacy_setting}
              onValueChange={(value) =>
                setSettings((prev) => ({ ...prev, privacy_setting: value }))
              }
            >
              <SelectTrigger id="privacy">
                <SelectValue placeholder="Select privacy setting" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PRIVATE">Private</SelectItem>
                <SelectItem value="PUBLIC">Public</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={settings.description}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, description: e.target.value }))
              }
              placeholder="Enter a description for your family tree..."
            />
          </div>
        </div>
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={loading}>
            {loading ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
