package migrate

import (
	"os"
	"path/filepath"
)

var migrateableFiles = []string{
	"AGENTS.md",
	"SOUL.md",
	"USER.md",
	"TOOLS.md",
	"HEARTBEAT.md",
}

var migrateableDirs = []string{
	"memory",
	"skills",
}

func PlanWorkspaceMigration(srcWorkspace, dstWorkspace string, force bool) ([]Action, error) {
	var actions []Action

	for _, filename := range migrateableFiles {
		src := filepath.Join(srcWorkspace, filename)
		dst := filepath.Join(dstWorkspace, filename)
		action := planFileCopy(src, dst, force)
		if action.Type != ActionSkip || action.Description != "" {
			actions = append(actions, action)
		}
	}

	for _, dirname := range migrateableDirs {
		srcDir := filepath.Join(srcWorkspace, dirname)
		if _, err := os.Stat(srcDir); os.IsNotExist(err) {
			continue
		}
		dirActions, err := planDirCopy(srcDir, filepath.Join(dstWorkspace, dirname), force)
		if err != nil {
			return nil, err
		}
		actions = append(actions, dirActions...)
	}

	return actions, nil
}

func planFileCopy(src, dst string, force bool) Action {
	if _, err := os.Stat(src); os.IsNotExist(err) {
		return Action{
			Type:        ActionSkip,
			Source:      src,
			Destination: dst,
			Description: "source file not found",
		}
	}

	_, dstExists := os.Stat(dst)
	if dstExists == nil && !force {
		return Action{
			Type:        ActionBackup,
			Source:      src,
			Destination: dst,
			Description: "destination exists, will backup and overwrite",
		}
	}

	return Action{
		Type:        ActionCopy,
		Source:      src,
		Destination: dst,
		Description: "copy file",
	}
}

func planDirCopy(srcDir, dstDir string, force bool) ([]Action, error) {
	var actions []Action

	err := filepath.Walk(srcDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		relPath, err := filepath.Rel(srcDir, path)
		if err != nil {
			return err
		}

		dst := filepath.Join(dstDir, relPath)

		if info.IsDir() {
			actions = append(actions, Action{
				Type:        ActionCreateDir,
				Destination: dst,
				Description: "create directory",
			})
			return nil
		}

		action := planFileCopy(path, dst, force)
		actions = append(actions, action)
		return nil
	})

	return actions, err
}
