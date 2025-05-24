import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTree } from "@/contexts/TreeContext";
import { ChevronDown, Plus } from "lucide-react";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function TreeSelector() {
  const { trees, activeTree, setActiveTree, createTree } = useTree();
  const [newTreeDialogOpen, setNewTreeDialogOpen] = useState(false);
  const [newTreeName, setNewTreeName] = useState("");
  const [newTreeDescription, setNewTreeDescription] = useState("");

  const handleCreateTree = async (e: React.FormEvent) => {
    e.preventDefault();
    await createTree({
      name: newTreeName,
      description: newTreeDescription,
    });
    setNewTreeDialogOpen(false);
    setNewTreeName("");
    setNewTreeDescription("");
  };

  return (
    <div className="flex items-center gap-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="min-w-[200px] justify-between">
            {activeTree?.name || "Select a tree"}
            <ChevronDown className="h-4 w-4 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[200px]">
          {trees.map((tree) => (
            <DropdownMenuItem
              key={tree.id}
              onSelect={() => setActiveTree(tree.id)}
            >
              {tree.name}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={newTreeDialogOpen} onOpenChange={setNewTreeDialogOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="icon">
            <Plus className="h-4 w-4" />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Tree</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateTree} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={newTreeName}
                onChange={(e) => setNewTreeName(e.target.value)}
                placeholder="My Family Tree"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={newTreeDescription}
                onChange={(e) => setNewTreeDescription(e.target.value)}
                placeholder="A brief description of your family tree..."
              />
            </div>
            <Button type="submit" className="w-full">
              Create Tree
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
