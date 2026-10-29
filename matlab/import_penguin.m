function import_penguin()
%IMPORT_PENGUIN  Independent multibody check of the penguin, in Simscape.
%
% The PyBullet model and this one are built from the *same* URDF, which in turn
% is generated from the Inventor mass properties - but the two solvers share no
% code. If they agree on the standing centre of mass, the joint tree and the
% static torques, the numbers are a property of the robot rather than of one
% physics engine.
%
% Writes penguin_sim.slx and prints the comparison.

    here = fileparts(mfilename('fullpath'));
    urdf = fullfile(fileparts(here), 'sim', 'penguin.urdf');
    if ~isfile(urdf)
        error('penguin.urdf not found - run sim/build_urdf.py first');
    end

    fprintf('importing %s\n', urdf);
    mdl = 'penguin_sim';
    if bdIsLoaded(mdl), close_system(mdl, 0); end
    cd(here);
    smimport(urdf, 'ModelName', mdl);
    save_system(mdl, fullfile(here, [mdl '.slx']));
    fprintf('model written: %s.slx\n', mdl);

    % ---- what the import found ------------------------------------------
    blocks = find_system(mdl, 'BlockType', 'SubSystem');
    % Simscape Multibody names each imported joint block after the URDF joint,
    % so look those up by name rather than guessing at a block type.
    jnames = {'leg_R','leg_L','foot_R','foot_L','flipper_R','flipper_L','beak'};
    found = {};
    for k = 1:numel(jnames)
        h = find_system(mdl, 'Name', jnames{k});
        if ~isempty(h), found{end+1} = jnames{k}; end %#ok<AGROW>
    end
    fprintf('\n  bodies (subsystems) : %d\n', numel(blocks));
    fprintf('  revolute joints     : %d of %d expected\n', numel(found), numel(jnames));
    fprintf('     %s\n', strjoin(found, ', '));

    % ---- mass check against the JSON the URDF came from ------------------
    jsonf = fullfile(fileparts(here), 'CAD', 'exports', 'mass_properties.json');
    if isfile(jsonf)
        j = jsondecode(fileread(jsonf));
        names = fieldnames(j.links);
        M = 0; num = zeros(1,3);
        for k = 1:numel(names)
            L = j.links.(names{k});
            M = M + L.mass;
            num = num + L.mass * L.com(:)';
        end
        com = num / M;
        fprintf('\n  from the CAD mass properties:\n');
        fprintf('    total mass      %7.1f g\n', M*1000);
        fprintf('    CoM             (%6.1f, %6.1f, %6.1f) mm\n', com*1000);
        fprintf('    CoM above floor %7.1f mm\n', com(3)*1000 - j.floor_z_mm);
        fprintf('    hip half-stance %7.1f mm\n', j.hip_x_mm);

        % static ankle torque standing on one foot
        lever = j.hip_x_mm/1000;
        tau = M * 9.81 * lever;
        stall = j.servo.stall_torque_Nm;
        fprintf('\n  single-foot ankle torque:\n');
        fprintf('    %.3f N.m = %.2f kg.cm  (%.0f%% of MG90S stall)\n', ...
                tau, tau*10.1972, 100*tau/stall);
    end

    fprintf(['\n  Open %s.slx and press Run to watch it fall over under gravity\n' ...
             '  with the joints free - that is the uncontrolled plant the balance\n' ...
             '  controller in sim/control.py has to stabilise.\n'], mdl);
end
