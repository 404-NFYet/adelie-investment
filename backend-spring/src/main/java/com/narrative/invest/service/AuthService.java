package com.narrative.invest.service;

import com.narrative.invest.dto.auth.AuthResponse;
import com.narrative.invest.dto.auth.LoginRequest;
import com.narrative.invest.dto.auth.RegisterRequest;
import com.narrative.invest.model.User;
import com.narrative.invest.repository.UserRepository;
import com.narrative.invest.security.JwtService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Lazy;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.regex.Pattern;

@Service
public class AuthService implements UserDetailsService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthenticationManager authenticationManager;

    // 차단할 이메일 도메인 (application.yml에서 주입)
    private final List<String> blockedDomains;

    // 차단할 사용자명 패턴 (application.yml에서 주입)
    private final Pattern blockedUsernamePattern;

    public AuthService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            JwtService jwtService,
            @Lazy AuthenticationManager authenticationManager,
            @Value("${registration.blocked-domains:tempmail.com,throwaway.email,guerrillamail.com,mailinator.com,yopmail.com}")
            List<String> blockedDomains,
            @Value("${registration.blocked-username-pattern:.*(admin|test|root|관리자|운영자|시발|씨발|개새|병신).*}")
            String blockedUsernamePatternStr
    ) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.authenticationManager = authenticationManager;
        this.blockedDomains = blockedDomains;
        this.blockedUsernamePattern = Pattern.compile(blockedUsernamePatternStr, Pattern.CASE_INSENSITIVE);
    }

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        return userRepository.findByEmail(username)
                .orElseThrow(() -> new UsernameNotFoundException("User not found: " + username));
    }

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        // 이메일 도메인 차단 검증
        validateEmailDomain(request.getEmail());

        // Check if user already exists
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new IllegalArgumentException("이미 등록된 이메일입니다.");
        }

        // Generate username if not provided
        String username = request.getUsername();
        if (username == null || username.isEmpty()) {
            username = request.getEmail().split("@")[0];
        }

        // 사용자명 부적절 패턴 차단 검증
        validateUsername(username);

        // Create new user
        User user = User.builder()
                .email(request.getEmail())
                .passwordHash(passwordEncoder.encode(request.getPassword()))
                .username(username)
                .difficultyLevel("beginner")
                .build();

        // Save user
        user = userRepository.save(user);

        // Generate tokens
        String accessToken = jwtService.generateToken(user);
        String refreshToken = jwtService.generateRefreshToken(user);

        return buildAuthResponse(user, accessToken, refreshToken);
    }

    public AuthResponse login(LoginRequest request) {
        // Authenticate
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(
                        request.getEmail(),
                        request.getPassword()
                )
        );

        // Get user
        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new UsernameNotFoundException("User not found"));

        // Update last login
        user.setLastLoginAt(java.time.LocalDateTime.now());
        userRepository.save(user);

        // Generate tokens
        String accessToken = jwtService.generateToken(user);
        String refreshToken = jwtService.generateRefreshToken(user);

        return buildAuthResponse(user, accessToken, refreshToken);
    }

    @Transactional
    public AuthResponse refreshToken(String refreshToken) {
        // Extract username from refresh token
        String username = jwtService.extractUsername(refreshToken);
        
        // Get user
        User user = userRepository.findByEmail(username)
                .orElseThrow(() -> new UsernameNotFoundException("User not found"));

        // Validate refresh token
        if (!jwtService.isTokenValid(refreshToken, user)) {
            throw new IllegalArgumentException("Refresh token expired");
        }

        // Generate new tokens
        String newAccessToken = jwtService.generateToken(user);
        String newRefreshToken = jwtService.generateRefreshToken(user);

        return buildAuthResponse(user, newAccessToken, newRefreshToken);
    }

    @Transactional
    public void logout(String email) {
        // In a stateless JWT system, logout is typically handled client-side
        // by discarding the token. Server-side, we just log the action.
        userRepository.findByEmail(email).ifPresent(user -> {
            // Could implement token blacklisting here if needed
        });
    }

    /**
     * 이메일 도메인 차단 검증.
     * 일회용 이메일 서비스 등 차단 대상 도메인 사용 시 예외 발생.
     */
    private void validateEmailDomain(String email) {
        if (email == null || !email.contains("@")) {
            throw new IllegalArgumentException("유효하지 않은 이메일 형식입니다.");
        }
        String domain = email.substring(email.indexOf("@") + 1).toLowerCase();
        for (String blocked : blockedDomains) {
            if (domain.equalsIgnoreCase(blocked.trim())) {
                throw new IllegalArgumentException("허용되지 않는 이메일 도메인입니다: " + domain);
            }
        }
    }

    /**
     * 사용자명 부적절 패턴 차단 검증.
     * 관리자 사칭, 비속어 등 부적절한 사용자명 사용 시 예외 발생.
     */
    private void validateUsername(String username) {
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("사용자명은 비어있을 수 없습니다.");
        }
        if (blockedUsernamePattern.matcher(username).matches()) {
            throw new IllegalArgumentException("사용할 수 없는 사용자명입니다.");
        }
    }

    private AuthResponse buildAuthResponse(User user, String accessToken, String refreshToken) {
        return AuthResponse.builder()
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .tokenType("Bearer")
                .expiresIn(86400L) // 24 hours
                .user(AuthResponse.UserInfo.builder()
                        .id(user.getId())
                        .email(user.getEmail())
                        .username(user.getUsername())
                        .build())
                .build();
    }
}
